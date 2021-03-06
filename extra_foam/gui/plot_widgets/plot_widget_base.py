"""
Distributed under the terms of the BSD 3-Clause License.

The full license is in the file LICENSE, distributed with this software.

Author: Jun Zhu <jun.zhu@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
import abc

import numpy as np

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QSizePolicy

from .. import pyqtgraph as pg

from .plot_items import (
    BarGraphItem, CurvePlotItem, StatisticsBarItem
)
from ..misc_widgets import FColor
from ...config import config
from ...typing import final


class PlotWidgetF(pg.GraphicsView):
    """PlotWidget base class.

    GraphicsView widget displaying a single PlotItem.

    Note: it is different from the PlotWidget in pyqtgraph.

    This base class should be used to display plots except images.
    For displaying images, please refer to ImageViewF class.
    """
    # signals wrapped from PlotItem / ViewBox
    sigRangeChanged = pyqtSignal(object, object)
    sigTransformChanged = pyqtSignal(object)

    def __init__(self, parent=None, *,
                 background='default', show_indicator=False, **kargs):
        """Initialization."""
        super().__init__(parent, background=background)
        try:
            parent.registerPlotWidget(self)
        except AttributeError:
            # if parent is None or parent has no such a method
            pass

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.enableMouse(False)

        self._title = ""

        # pg.PlotItem is a QGraphicsWidget
        self._plot_item = pg.PlotItem(**kargs)
        # set 'centralWidget' for GraphicsView and add the item to
        # GraphicsScene
        self.setCentralItem(self._plot_item)

        self._show_indicator = show_indicator
        if show_indicator:
            self._v_line = pg.InfiniteLine(angle=90, movable=False)
            self._h_line = pg.InfiniteLine(angle=0, movable=False)
            self._indicator = pg.TextItem(color=FColor.k)
            self._v_line.hide()
            self._h_line.hide()
            self._indicator.hide()
            self._plot_item.addItem(self._v_line, ignoreBounds=True)
            self._plot_item.addItem(self._h_line, ignoreBounds=True)
            self._plot_item.scene().addItem(self._indicator)

            # rateLimit should be fast enough to be able to capture
            # the leaveEvent
            self._proxy = pg.SignalProxy(self._plot_item.scene().sigMouseMoved,
                                         rateLimit=60, slot=self.onMouseMoved)

        self._vb2 = None  # ViewBox for y2 axis

        self._plot_item.sigRangeChanged.connect(self.viewRangeChanged)

    def clear(self):
        """Remove all the items in the PlotItem object."""
        plot_item = self._plot_item
        for i in plot_item.items[:]:
            plot_item.removeItem(i)

    def reset(self):
        """Clear the data of all the items in the PlotItem object."""
        for item in self._plot_item.items:
            try:
                item.setData([], [])
            except TypeError:
                # FIXME: better solution
                pass

    @abc.abstractmethod
    def updateF(self, data):
        """This method is called by the parent window."""
        raise NotImplementedError

    def close(self):
        self._plot_item.close()
        self._plot_item = None
        self.setParent(None)
        super().close()

    def addItem(self, *args, **kwargs):
        """Explicitly call PlotItem.addItem.

        This method must be here to override the addItem method in
        GraphicsView. Otherwise, people may misuse the addItem method.
        """
        self._plot_item.addItem(*args, **kwargs)

    def removeItem(self, *args, **kwargs):
        self._plot_item.removeItem(*args, **kwargs)

    def plotCurve(self, *args, **kwargs):
        """Add and return a new curve plot."""
        item = pg.PlotCurveItem(*args, **kwargs)
        self._plot_item.addItem(item)
        return item

    def plotScatter(self, *args, **kwargs):
        """Add and return a new scatter plot."""
        if 'pen' not in kwargs:
            kwargs['pen'] = FColor.mkPen(None)
        item = pg.ScatterPlotItem(*args, **kwargs)
        self._plot_item.addItem(item)
        return item

    def plotBar(self, x=None, y=None, width=1.0, y2=False, **kwargs):
        """Add and return a new bar plot."""
        item = BarGraphItem(x=x, y=y, width=width, **kwargs)

        if y2:
            if self._vb2 is None:
                self.createY2()
            self._vb2.addItem(item)
        else:
            self._plot_item.addItem(item)

        return item

    def plotStatisticsBar(self, x=None, y=None, y_min=None, y_max=None,
                          beam=None, y2=False, **kwargs):
        item = StatisticsBarItem(x=x, y=y, y_min=y_min, y_max=y_max,
                                 beam=beam, **kwargs)
        if y2:
            if self._vb2 is None:
                self.createY2()
            self._vb2.addItem(item)
        else:
            self._plot_item.addItem(item)

        return item

    def plotImage(self, *args, **kargs):
        """Add and return a image item."""
        # TODO: this will be done when another branch is merged
        raise NotImplemented

    def createY2(self):
        vb = pg.ViewBox()
        plot_item = self._plot_item
        plot_item.scene().addItem(vb)
        plot_item.getAxis('right').linkToView(vb)
        vb.setXLink(self._plot_item.vb)
        self._plot_item.vb.sigResized.connect(self.updateY2View)
        self._vb2 = vb

    def updateY2View(self):
        vb = self._vb2
        if vb is None:
            return
        # update ViewBox-y2 to match ViewBox-y
        vb.setGeometry(self._plot_item.vb.sceneBoundingRect())
        # not sure this is required
        # vb.linkedViewChanged(self._plot_item.vb, vb.XAxis)

    def setAspectLocked(self, *args, **kwargs):
        self._plot_item.setAspectLocked(*args, **kwargs)

    def setLabel(self, *args, **kwargs):
        self._plot_item.setLabel(*args, **kwargs)

    def setTitle(self, *args, **kwargs):
        self._plot_item.setTitle(*args, **kwargs)

    def addLegend(self, *args, **kwargs):
        self._plot_item.addLegend(*args, **kwargs)

    def hideAxis(self):
        for v in ["left", 'bottom']:
            self._plot_item.hideAxis(v)

    def showAxis(self):
        for v in ["left", 'bottom']:
            self._plot_item.showAxis(v)

    def viewRangeChanged(self, view, range):
        self.sigRangeChanged.emit(self, range)

    def saveState(self):
        return self._plot_item.saveState()

    def restoreState(self, state):
        return self._plot_item.restoreState(state)

    def onMouseMoved(self, ev):
        pos = ev[0]
        y_shift = 45  # move text to the top of the mouse cursor
        self._indicator.setPos(pos.x(), pos.y() - y_shift)

        m_pos = self._plot_item.vb.mapSceneToView(pos)
        x, y = m_pos.x(), m_pos.y()
        self._v_line.setPos(x)
        self._h_line.setPos(y)

        self._indicator.setText(f"x={x}\ny={y}")

    def enterEvent(self, ev):
        """Override."""
        if self._show_indicator:
            self._v_line.show()
            self._h_line.show()
            self._indicator.show()

    def leaveEvent(self, ev):
        """Override."""
        if self._show_indicator:
            self._v_line.hide()
            self._h_line.hide()
            self._indicator.hide()

    def closeEvent(self, QCloseEvent):
        parent = self.parent()
        if parent is not None:
            parent.unregisterPlotWidget(self)
        super().closeEvent(QCloseEvent)


class TimedPlotWidgetF(PlotWidgetF):
    def __init__(self, *args, **kwargs):
        """Initialization."""
        super().__init__(*args, **kwargs)

        self._data = None

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_imp)
        self._timer.start(config["GUI_PLOT_WITH_STATE_UPDATE_TIMER"])

    @abc.abstractmethod
    def refresh(self):
        pass

    def _refresh_imp(self):
        if self._data is not None:
            self.refresh()

    @final
    def updateF(self, data):
        """Override."""
        self._data = data


class HistMixin:
    def updateTitle(self, mean=np.nan, median=np.nan, std=np.nan):
        self.setTitle(self._title_template.substitute(
            mean=f"{mean:.2e}", median=f"{median:.2e}", std=f"{std:.2e}"))

    def reset(self):
        super().reset()
        self.updateTitle()
