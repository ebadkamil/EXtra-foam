"""
Distributed under the terms of the BSD 3-Clause License.

The full license is in the file LICENSE, distributed with this software.

Author: Jun Zhu <jun.zhu@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
import math

import numpy as np

from .special_analysis_base import ProcessingError, QThreadWorker
from ..algorithms import hist_with_stats
from ..pipeline.data_model import MovingAverageArray
from ..utils import profiler
from ..config import _MAX_INT32


_PIXEL_DTYPE = np.float32


class GotthardProcessor(QThreadWorker):
    """Gotthard analysis processor.

    Attributes:
        _output_channel (str): output channel name.
        _pulse_slicer (slice): a slice used to slice pulses in a train.
        _poi_index (int): index of the pulse of interest after slicing.
        _bin_range (tuple): range of the ADU histogram.
        _n_bins (int): number of bins of the ADU histogram.
        _hist_over_ma (bool): True for calculating the histogram over the
            moving averaged data. Otherwise, it is calculated over the
            current train.
        _raw_ma (numpy.ndarray): moving average of the raw data.
            Shape=(pulses, pixels)
        _dark_ma (numpy.ndarray): moving average of the dark data.
            Shape=(pulses, pixels)
        _dark_mean_ma (numpy.ndarray): average of pulses in a train of the
            moving average of the dark data. It is used for dark subtraction.
            Shape=(pixels,)
    """

    _DATA_PROPERTY = "data.adc"

    _raw_ma = MovingAverageArray()
    _dark_ma = MovingAverageArray(_MAX_INT32)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._output_channel = ""

        self._pulse_slicer = slice(None, None)
        self._poi_index = 0

        self._bin_range = (-math.inf, math.inf)
        self._n_bins = 10
        self._hist_over_ma = False

        self._setMaWindow(1)

        del self._dark_ma
        self._dark_mean_ma = None

    def _setMaWindow(self, v):
        self.__class__._raw_ma.window = v

    def onOutputChannelChanged(self, ch: str):
        self._output_channel = ch

    def onMaWindowChanged(self, value: str):
        self._setMaWindow(int(value))

    def onBinRangeChanged(self, value: tuple):
        self._bin_range = value

    def onNoBinsChanged(self, value: str):
        self._n_bins = int(value)

    def onHistOverMaChanged(self, state: bool):
        self._hist_over_ma = state

    def onPulseSlicerChanged(self, value: list):
        self._pulse_slicer = slice(*value)
        dark_ma = self._dark_ma
        if dark_ma is not None:
            self._dark_mean_ma = np.mean(dark_ma[self._pulse_slicer], axis=0)

    def onPoiIndexChanged(self, value: int):
        self._poi_index = value

    def onLoadDarkRun(self, dirpath):
        """Override."""
        run = self._loadRunDirectory(dirpath)
        if run is not None:
            try:
                arr = run.get_array(self._output_channel, self._DATA_PROPERTY)
                shape = arr.shape
                if arr.ndim != 3:
                    self.log.error(f"Data must be a 3D array! "
                                   f"Actual shape: {shape}")
                    return

                self.log.info(f"Found dark data with shape {shape}")
                # FIXME: performance
                self._dark_ma = np.mean(
                    arr.values, axis=0, dtype=_PIXEL_DTYPE)
                self._dark_mean_ma = np.mean(
                    self._dark_ma[self._pulse_slicer],
                    axis=0, dtype=_PIXEL_DTYPE)
            except Exception as e:
                self.log.error(f"Unexpect exception when getting data array: "
                               f"{repr(e)}")

    def onRemoveDark(self):
        """Override."""
        del self._dark_ma
        self._dark_mean_ma = None

    @profiler("Gotthard Processor")
    def process(self, data):
        """Override."""
        data, _ = data

        data = data[self._output_channel]
        tid = data['metadata']["timestamp.tid"]

        try:
            raw = data[self._DATA_PROPERTY].astype(_PIXEL_DTYPE)
        except KeyError:
            raise ProcessingError(f"Gotthard data must contain property "
                                  f"'{self._DATA_PROPERTY}'")

        # check data shape
        if raw.ndim != 2:
            raise ProcessingError(f"Gotthard data must be a 2D array: "
                                  f"actual {raw.ndim}D")

        # check POI index
        max_idx = raw[self._pulse_slicer].shape[0]
        if self._poi_index >= max_idx:
            raise ProcessingError(f"POI index {self._poi_index} out of "
                                  f"boundary [{0} - {max_idx - 1}]")

        # ------------
        # process data
        # ------------

        if self._recording_dark:
            # update the moving average of dark data
            self._dark_ma = raw

            self._dark_mean_ma = np.mean(
                self._dark_ma[self._pulse_slicer], axis=0)

            # During dark recording, no offset correcttion is applied and
            # only dark data and its statistics are displayed.
            displayed = raw[self._pulse_slicer]
            displayed_ma = self._dark_ma[self._pulse_slicer]
        else:
            # update the moving average of raw data
            self._raw_ma = raw

            if self._subtract_dark and self._dark_mean_ma is not None:
                displayed = raw[self._pulse_slicer] - self._dark_mean_ma
                displayed_ma = self._raw_ma[self._pulse_slicer] - self._dark_mean_ma
            else:
                displayed = raw[self._pulse_slicer]
                displayed_ma = self._raw_ma[self._pulse_slicer]

        mean = np.mean(displayed, axis=0)
        mean_ma = np.mean(displayed_ma, axis=0)

        self.log.info(f"Train {tid} processed")

        return {
            # index of pulse of interest
            "poi_index": self._poi_index,
            # 2D data for the current train
            "displayed": displayed,
            # 2D data for the moving averaged train
            "displayed_ma": displayed_ma,
            # average of the displayed data for the current train over pulse
            "mean": mean,
            # average of the moving averaged displayed train data over pulse
            "mean_ma": mean_ma,
            # (hist, bin_centers, mean, median, std)
            "hist": hist_with_stats(
                displayed_ma if self._hist_over_ma else displayed,
                self._bin_range, self._n_bins),
        }
