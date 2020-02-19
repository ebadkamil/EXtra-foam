import unittest
from unittest.mock import MagicMock, patch
from collections import Counter, deque

from PyQt5.QtWidgets import QMainWindow

from extra_foam.logger import logger
from extra_foam.gui import mkQApp
from extra_foam.gui.windows import (
    BinningWindow, CorrelationWindow, HistogramWindow, PumpProbeWindow, RoiWindow
)
from extra_foam.gui.plot_widgets import RoiImageView
from extra_foam.pipeline.data_model import ProcessedData

app = mkQApp()

logger.setLevel('CRITICAL')


class TestPlotWindows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = QMainWindow()  # dummy MainGUI
        cls.gui.registerWindow = MagicMock()
        cls.gui.registerSpecialWindow = MagicMock()

    @classmethod
    def tearDownClass(cls):
        cls.gui.close()

    def testPumpProbeWindow(self):
        from extra_foam.gui.windows.pump_probe_w import (
            PumpProbeImageView, PumpProbeVFomPlot, PumpProbeFomPlot
        )
        win = PumpProbeWindow(deque(), pulse_resolved=True, parent=self.gui)

        self.assertEqual(5, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(2, counter[PumpProbeImageView])
        self.assertEqual(2, counter[PumpProbeVFomPlot])
        self.assertEqual(1, counter[PumpProbeFomPlot])

        win.updateWidgetsF()

    def testRoiWindow(self):
        win = RoiWindow(deque(), pulse_resolved=True, parent=self.gui)

        self.assertEqual(2, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(2, counter[RoiImageView])

        win.updateWidgetsF()

    def testBinningWindow(self):
        from extra_foam.gui.windows.binning_w import Bin1dHeatmap, Bin1dHist, Bin2dHeatmap

        win = BinningWindow(deque(maxlen=1), pulse_resolved=True, parent=self.gui)

        self.assertEqual(4, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(1, counter[Bin1dHeatmap])
        self.assertEqual(1, counter[Bin1dHist])
        self.assertEqual(2, counter[Bin2dHeatmap])

        win.updateWidgetsF()

    def testCorrelationWindow(self):
        from extra_foam.gui.windows.correlation_w import CorrelationPlot

        win = CorrelationWindow(deque(maxlen=1), pulse_resolved=True, parent=self.gui)

        self.assertEqual(2, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(2, counter[CorrelationPlot])

        win.updateWidgetsF()

    def testHistogramWindow(self):
        from extra_foam.gui.windows.histogram_w import FomHist, InTrainFomPlot

        win = HistogramWindow(deque(maxlen=1), pulse_resolved=True, parent=self.gui)

        self.assertEqual(2, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(1, counter[InTrainFomPlot])
        self.assertEqual(1, counter[FomHist])

        win.updateWidgetsF()

    def testPulseOfInterestWindow(self):
        from extra_foam.gui.windows.pulse_of_interest_w import (
            PulseOfInterestWindow, PoiImageView, PoiHist
        )

        win = PulseOfInterestWindow(deque(), pulse_resolved=True, parent=self.gui)

        self.assertEqual(4, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(2, counter[PoiImageView])
        self.assertEqual(2, counter[PoiHist])

        win.updateWidgetsF()

    def testTrXasWindow(self):
        from extra_foam.gui.windows.tri_xas_w import (
            TrXasWindow, TrXasAbsorptionPlot, TrXasHeatmap
        )
        win = TrXasWindow(deque(), pulse_resolved=True, parent=self.gui)

        self.assertEqual(6, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(3, counter[RoiImageView])
        self.assertEqual(2, counter[TrXasAbsorptionPlot])
        self.assertEqual(1, counter[TrXasHeatmap])

        win.updateWidgetsF()


class testPumpProbeWidgets(unittest.TestCase):
    def testPumpProbeImageView(self):
        from extra_foam.gui.windows.pump_probe_w import PumpProbeImageView

        widget = PumpProbeImageView()
        data = ProcessedData(1)
        widget.updateF(data)

    def testPumpProbeVFomPlot(self):
        from extra_foam.gui.windows.pump_probe_w import PumpProbeVFomPlot

        widget = PumpProbeVFomPlot()
        data = ProcessedData(1)
        widget.updateF(data)

    def testPumpProbeFomPlot(self):
        from extra_foam.gui.windows.pump_probe_w import PumpProbeFomPlot

        widget = PumpProbeFomPlot()
        widget._data = ProcessedData(1)
        widget.refresh()


class testPulseOfInterestWidgets(unittest.TestCase):
    def testPoiImageView(self):
        from extra_foam.gui.windows.pulse_of_interest_w import PoiImageView

        widget = PoiImageView(0)
        data = ProcessedData(1)
        widget.updateF(data)

    def testPoiHist(self):
        from extra_foam.gui.windows.pulse_of_interest_w import PoiHist

        widget = PoiHist(0)
        widget._data = ProcessedData(1)
        widget.refresh()


class testBinningWidgets(unittest.TestCase):
    def testHeatmap1D(self):
        from extra_foam.gui.windows.binning_w import Bin1dHeatmap

        widget = Bin1dHeatmap()
        widget._data = ProcessedData(1)

        # test "Auto level" reset
        widget._auto_level = True
        widget.refresh()
        self.assertFalse(widget._auto_level)

    def testHeatmap2D(self):
        from extra_foam.gui.windows.binning_w import Bin2dHeatmap

        for is_count in [False, True]:
            widget = Bin2dHeatmap(count=is_count)
            widget._data = ProcessedData(1)

            # test "Auto level" reset
            widget._auto_level = True
            widget.refresh()
            self.assertFalse(widget._auto_level)


class testCorrrelationWidgets(unittest.TestCase):
    def testGeneral(self):
        from extra_foam.gui.windows.correlation_w import CorrelationPlot

        for i in range(2):
            widget = CorrelationPlot(0)
            widget._data = ProcessedData(1)
            widget.refresh()


class testHistogramWidgets(unittest.TestCase):
    def testFomHist(self):
        from extra_foam.gui.windows.histogram_w import FomHist

        widget = FomHist()
        widget._data = ProcessedData(1)
        widget.refresh()

    def testInTrainFomPlot(self):
        from extra_foam.gui.windows.histogram_w import InTrainFomPlot

        widget = InTrainFomPlot()
        data = ProcessedData(1)
        widget.updateF(data)


class testTriXasWidgets(unittest.TestCase):
    def testTrXasAbsorptionPlot(self):
        from extra_foam.gui.windows.tri_xas_w import TrXasAbsorptionPlot

        widget = TrXasAbsorptionPlot()

    def testTrXasHeatmap(self):
        from extra_foam.gui.windows.tri_xas_w import TrXasHeatmap

        widget = TrXasHeatmap()
