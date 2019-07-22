"""
Offline and online data analysis and visualization tool for azimuthal
integration of different data acquired with various detectors at
European XFEL.

Concrete PlotWidgets.

Author: Jun Zhu <jun.zhu@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
import numpy as np

from .base_plot_widget import PlotWidget

from ..misc_widgets import make_brush, make_pen, SequentialColors
from ...config import AnalysisType, config


class TrainAiWidget(PlotWidget):
    """TrainAiWidget class.

    Widget for displaying azimuthal integration result for the average of all
    the pulse(s) in a train.
    """
    def __init__(self, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self.setLabel('bottom', "Momentum transfer (1/A)")
        self.setLabel('left', "Scattering signal (arb. u.)")

        self._plot = self.plotCurve(pen=make_pen("p"))

    def update(self, data):
        """Override."""
        momentum = data.ai.x
        intensity = data.ai.vfom

        if intensity is None:
            return

        self._plot.setData(momentum, intensity)


class PulsesInTrainFomWidget(PlotWidget):
    """PulsesInTrainFomWidget class.

    A widget which allows users to monitor the FOM of each pulse in a train.
    """
    def __init__(self, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self._plot = self.plotBar()

        self.setLabel('left', "FOM")
        self.setLabel('bottom', "Pulse index")
        self.setTitle('Analysis type')

    def update(self, data):
        """Override."""
        fom_list = None
        analysis_type = data.st.analysis_type
        if analysis_type == AnalysisType.AZIMUTHAL_INTEG_PULSE:
            fom_list = data.pulse.ai.fom
        elif analysis_type == AnalysisType.ROI1_PULSE:
            fom_list = data.pulse.roi.roi1.fom

        if fom_list is None:
            return

        self._plot.setData(range(len(fom_list)), fom_list)


class CorrelationWidget(PlotWidget):
    """CorrelationWidget class.

    Widget for displaying correlations between FOM and different parameters.
    """
    _colors = config["CORRELATION_COLORS"]
    _pens = [make_pen(color) for color in _colors]
    _brushes = [make_brush(color, 120) for color in _colors]
    _opaque_brushes = [make_brush(color) for color in _colors]

    def __init__(self, idx, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self._idx = idx  # start from 1

        self.setLabel('left', "FOM (arb. u.)")
        self.setLabel('bottom', "Correlator (arb. u.)")

        self._bar = self.plotErrorBar(pen=self._pens[self._idx-1])
        self._plot = self.plotScatter(brush=self._brushes[self._idx-1])

        self._device_id = None
        self._ppt = None
        self._resolution = 0.0

    def update(self, data):
        """Override."""
        correlator_hist, fom_hist, info = getattr(
            data.corr, f'correlation{self._idx}').hist

        device_id = info['device_id']
        ppt = info['property']
        if self._device_id != device_id or self._ppt != ppt:
            self.setLabel('bottom', f"{device_id + ' | ' + ppt} (arb. u.)")
            self._device_id = device_id
            self._ppt = ppt

        if isinstance(fom_hist, np.ndarray):
            # PairData
            if self._resolution != 0.0:
                self._resolution = 0.0
                self._bar.setData([], [], beam=0.0)
                self._plot.setBrush(self._brushes[self._idx-1])

            self._plot.setData(correlator_hist, fom_hist)
            # make auto-range of the viewbox work correctly
            self._bar.setData(correlator_hist, fom_hist)
        else:
            # AccumulatedPairData
            resolution = info['resolution']

            if self._resolution != resolution:
                self._resolution = resolution
                self._bar.setData([], [], beam=resolution)
                self._plot.setBrush(self._opaque_brushes[self._idx-1])

            self._bar.setData(x=correlator_hist,
                              y=fom_hist.avg,
                              y_min=fom_hist.min,
                              y_max=fom_hist.max)
            self._plot.setData(correlator_hist, fom_hist.avg)


class PumpProbeOnOffWidget(PlotWidget):
    """PumpProbeOnOffWidget class.

    Widget for displaying the pump and probe signal or their difference.
    """
    def __init__(self, diff=False, *, parent=None):
        """Initialization.

        :param bool diff: True for displaying on-off while False for
            displaying on and off
        """
        super().__init__(parent=parent)

        # self.setLabel('left', "Scattering signal (arb. u.)")
        # self.setLabel('bottom', "Momentum transfer (1/A)")
        self.setLabel('left', "y (arb. u.)")
        self.setLabel('bottom', "x (arb. u.)")
        self.addLegend(offset=(-40, 20))

        self._is_diff = diff
        if diff:
            self._on_off_pulse = self.plotCurve(name="On - Off", pen=make_pen("p"))
        else:
            self._on_pulse = self.plotCurve(name="On", pen=make_pen("r"))
            self._off_pulse = self.plotCurve(name="Off", pen=make_pen("b"))

    def update(self, data):
        """Override."""
        x = data.pp.x
        on = data.pp.vfom_on
        off = data.pp.vfom_off
        vfom = data.pp.vfom

        if on is None or off is None:
            return

        if isinstance(on, np.ndarray) and on.ndim > 1:
            # call reset() to reset() plots from other analysis types
            self.reset()
            return

        if self._is_diff:
            self._on_off_pulse.setData(x, vfom)
        else:
            self._on_pulse.setData(x, on)
            self._off_pulse.setData(x, off)


class PumpProbeFomWidget(PlotWidget):
    """PumpProbeFomWidget class.

    Widget for displaying the evolution of FOM in pump-probe analysis.
    """

    def __init__(self, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self.setLabel('bottom', "Train ID")
        self.setLabel('left', "FOM (arb. u.)")

        self._plot = self.plotScatter(brush=make_brush('g'))

    def update(self, data):
        """Override."""
        tids, fom_hist, _ = data.pp.fom_hist
        self._plot.setData(tids, fom_hist)


class XasSpectrumWidget(PlotWidget):
    """XasSpectrumWidget class.

    Widget for displaying the XAS spectra.
    """

    def __init__(self, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self.setLabel('bottom', "Energy (eV)")
        self.setLabel('left', "Absorption")

        self._spectrum1 = self.plotScatter(
            name="ROI2/ROI1", brush=make_brush('r'), size=12)
        self._spectrum2 = self.plotScatter(
            name="ROI3/ROI1", brush=make_brush('b'), size=12)

        self.addLegend(offset=(-40, 20))

    def update(self, data):
        """Override."""
        bin_center = data.xas.bin_center
        absorptions = data.xas.absorptions

        self._spectrum1.setData(bin_center, absorptions[0])
        self._spectrum2.setData(bin_center, absorptions[1])


class XasSpectrumDiffWidget(PlotWidget):
    """XasSpectrumDiffWidget class.

    Widget for displaying the difference of two XAS spectra.
    """

    def __init__(self, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self.setLabel('bottom', "Energy (eV)")
        self.setLabel('left', "Absorption")

        self._plot = self.plotScatter(brush=make_brush('b'), size=12)

    def update(self, data):
        """Override."""
        bin_center = data.xas.bin_center
        absorptions = data.xas.absorptions

        self._plot.setData(bin_center, absorptions[1] - absorptions[0])


class XasSpectrumBinCountWidget(PlotWidget):
    """XasSpectrumBinCountWidget class.

    Widget for displaying the number of data points in each energy bins.
    """

    def __init__(self, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent)

        self.setLabel('bottom', "Energy (eV)")
        self.setLabel('left', "Count")

        self._plot = self.plotBar()

    def update(self, data):
        """Override."""
        bin_center = data.xas.bin_center
        bin_count = data.xas.bin_count

        self._plot.setData(bin_center, bin_count)


class Bin1dHist(PlotWidget):
    """Bin1dHist class.

    Widget for visualizing histogram of count for 1D-binning.
    """
    def __init__(self, idx, *, count=False, parent=None):
        """Initialization.

        :param int idx: index of the binning parameter (must be 1 or 2).
        :param bool count: True for count plot and False for FOM plot.
        """
        super().__init__(parent=parent)

        self._idx = idx
        self._count = count

        self.setLabel('bottom', f"Label{idx}")
        if count:
            self.setLabel('left', "Count")
            self._plot = self.plotBar(pen=make_pen('g'), brush=make_brush('b'))
        else:
            self.setLabel('left', "FOM")
            self._plot = self.plotBar(pen=make_pen('g'), brush=make_brush('p'))

    def update(self, data):
        """Override."""
        if self._count:
            value = getattr(data.bin, f"count{self._idx}_hist")
        else:
            value = getattr(data.bin, f"fom{self._idx}_hist")

        reset = getattr(data.bin, f"reset{self._idx}")
        # do not update if FOM is None
        if value is not None and (reset or getattr(data.bin, f"fom{self._idx}") is not None):
            self._plot.setData(getattr(data.bin, f"center{self._idx}"), value)

            self.setLabel('bottom', getattr(data.bin, f"label{self._idx}"))
