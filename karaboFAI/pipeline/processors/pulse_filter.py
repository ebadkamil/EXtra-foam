"""
Offline and online data analysis and visualization tool for azimuthal
integration of different data acquired with various detectors at
European XFEL.

Author: Jun Zhu <jun.zhu@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
import numpy as np

from .base_processor import _BaseProcessor
from ..exceptions import ProcessingError
from ...database import Metadata as mt
from ...config import AnalysisType
from ...utils import profiler


class PulseFilterProcessor(_BaseProcessor):
    """PulseFilterProcessor class.

    Apply filters to pulse-resolved data.

    Attributes:
        analysis_type (AnalysisType): analysis type.
        _fom_range (tuple): if the FOM falls within this range, we will
            acknowledge the data.
        _xgm_intensity_range (tuple):  if the pulsed XGM intensity falls
            within this range, we will acknowledge the data.
    """
    def __init__(self):
        super().__init__()

        self.analysis_type = AnalysisType.UNDEFINED
        self._fom_range = (-np.inf, np.inf)
        self._xgm_intensity_range = (0, np.inf)

    def update(self):
        """Override."""
        cfg = self._meta.get_all(mt.PULSE_FILTER_PROC)

        self._update_analysis(AnalysisType(int(cfg['analysis_type'])))
        self._fom_range = self.str2tuple(cfg['fom_range'])
        self._xgm_intensity_range = self.str2tuple(cfg["xgm_intensity_range"])

    @profiler("Pulse filter processor")
    def process(self, data):
        if self.analysis_type == AnalysisType.UNDEFINED:
            return
        processed = data['processed']

        if self.analysis_type == AnalysisType.ROI1_PULSE:
            foms = processed.pulse.roi.roi1.fom
            if foms is None:
                raise ProcessingError(
                    "[Pulse filter]: "
                    "Pulse resolved ROI1 sum result is not available")
        elif self.analysis_type == AnalysisType.ROI2_PULSE:
            foms = processed.pulse.roi.roi2.fom
            if foms is None:
                raise ProcessingError(
                    "[Pulse filter]: "
                    "Pulse resolved ROI2 sum result is not available")
        else:
            raise NotImplementedError(
                f'[Pulse filter]: {repr(self.analysis_type)}')

        dropped = []  # a list of dropped indices
        lb, ub = self._fom_range[0], self._fom_range[1]
        for i, fom in enumerate(foms):
            if fom < lb or fom > ub:
                dropped.append(i)

        processed.image.dropped_indices = dropped