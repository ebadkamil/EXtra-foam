"""
Distributed under the terms of the BSD 3-Clause License.

The full license is in the file LICENSE, distributed with this software.

Author: Jun Zhu <jun.zhu@xfel.eu>, Ebad Kamil <ebad.kamil@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSplitter

from .base_window import _AbstractPlotWindow
from ..misc_widgets import FColor
from ..plot_widgets import TimedPlotWidgetF
from ...config import config


class CorrelationPlot(TimedPlotWidgetF):
    """CorrelationPlot class.

    Widget for displaying correlations between FOM and different parameters.
    """
    _colors = config["GUI_CORRELATION_COLORS"]
    _pens = [(FColor.mkPen(pair[0]), FColor.mkPen(pair[1])) for pair in _colors]
    _brushes = [(FColor.mkBrush(pair[0], alpha=120),
                 FColor.mkBrush(pair[1], alpha=120)) for pair in _colors]

    def __init__(self, idx, *, parent=None):
        """Initialization."""
        super().__init__(parent=parent, show_indicator=True)

        self._idx = idx

        self.setTitle(f'Correlation {idx+1}')
        self._default_x_label = "Correlator (arb. u.)"
        self._default_y_label = "FOM (arb. u.)"

        self._source = ""
        self._resolution = 0.0

        self.updateLabel()

        brush_pair = self._brushes[self._idx]
        self._plot = self.plotScatter(brush=brush_pair[0])
        self._plot_slave = self.plotScatter(brush=brush_pair[1])

    def refresh(self):
        """Override."""
        item = self._data.corr[self._idx]

        src = item.source
        if src != self._source:
            self._source = src
            self.updateLabel()

        resolution = item.resolution
        y = item.y
        y_slave = item.y_slave
        if resolution == 0:
            # SimplePairSequence
            if self._resolution != 0:
                self._newScatterPlot()
                self._resolution = 0

            self._plot.setData(item.x, y)
            if y_slave is not None:
                self._plot_slave.setData(item.x_slave, y_slave)
        else:
            # OneWayAccuPairSequence
            if self._resolution == 0:
                self._newStatisticsBarPlot(resolution)
                self._resolution = resolution
            self._plot.setData(item.x, y.avg, y_min=y.min, y_max=y.max)
            if y_slave is not None:
                self._plot_slave.setData(
                    item.x_slave, y_slave.avg,
                    y_min=y_slave.min, y_max=y_slave.max)

    def updateLabel(self):
        src = self._source
        if src:
            new_label = f"{src} (arb. u.)"
        else:
            new_label = self._default_x_label
        self.setLabel('bottom', new_label)

        self.setLabel('left', self._default_y_label)

    def _newScatterPlot(self):
        self.removeItem(self._plot)
        self.removeItem(self._plot_slave)

        brush_pair = self._brushes[self._idx]
        self._plot = self.plotScatter(brush=brush_pair[0])
        self._plot_slave = self.plotScatter(brush=brush_pair[1])

    def _newStatisticsBarPlot(self, resolution):
        self.removeItem(self._plot)
        self.removeItem(self._plot_slave)

        pen_pair = self._pens[self._idx]
        self._plot = self.plotStatisticsBar(beam=resolution, pen=pen_pair[0])
        self._plot_slave = self.plotStatisticsBar(beam=resolution,
                                                  pen=pen_pair[1])


class CorrelationWindow(_AbstractPlotWindow):
    """CorrelationWindow class.

    Visualize correlation.
    """
    _title = "Correlation"

    _TOTAL_W, _TOTAL_H = config['GUI_PLOT_WINDOW_SIZE']
    _TOTAL_H /= 2

    def __init__(self, *args, **kwargs):
        """Initialization."""
        super().__init__(*args, **kwargs)

        self._corr1 = CorrelationPlot(0, parent=self)
        self._corr2 = CorrelationPlot(1, parent=self)

        self.initUI()

        self.resize(self._TOTAL_W, self._TOTAL_H)
        self.setMinimumSize(0.6*self._TOTAL_W, 0.6*self._TOTAL_H)

        self.update()

    def initUI(self):
        """Override."""
        self._cw = QSplitter()
        self._cw.addWidget(self._corr1)
        self._cw.addWidget(self._corr2)
        self._cw.setSizes([1, 1])

        self.setCentralWidget(self._cw)

    def initConnections(self):
        """Override."""
        pass
