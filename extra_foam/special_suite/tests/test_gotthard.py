import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from collections import Counter

import pytest
import numpy as np
from xarray import DataArray

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QSignalSpy, QTest

from extra_foam.logger import logger_suite as logger
from extra_foam.gui import mkQApp
from extra_foam.special_suite.gotthard_proc import GotthardProcessor
from extra_foam.special_suite.gotthard_w import (
    GotthardWindow, GotthardImageView, GotthardAvgPlot, GotthardPulsePlot,
    GotthardHist
)
from extra_foam.special_suite.special_analysis_base import (
    ProcessingError
)

app = mkQApp()

logger.setLevel('CRITICAL')


class TestGotthard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("extra_foam.special_suite.special_analysis_base._SpecialAnalysisBase.startWorker"):
            cls._win = GotthardWindow('MID')

    @classmethod
    def tearDown(cls):
        # explicitly close the MainGUI to avoid error in GuiLogger
        cls._win.close()

    def testWindow(self):
        win = self._win

        self.assertEqual(4, len(win._plot_widgets))
        counter = Counter()
        for key in win._plot_widgets:
            counter[key.__class__] += 1

        self.assertEqual(1, counter[GotthardImageView])
        self.assertEqual(1, counter[GotthardAvgPlot])
        self.assertEqual(1, counter[GotthardPulsePlot])
        self.assertEqual(1, counter[GotthardHist])

        win.updateWidgetsF()

    def testCtrl(self):
        from extra_foam.special_suite.gotthard_w import _DEFAULT_N_BINS, _DEFAULT_BIN_RANGE

        default_bin_range = tuple(float(v) for v in _DEFAULT_BIN_RANGE.split(','))

        win = self._win
        ctrl_widget = win._ctrl_widget
        proc = win._worker

        # test default values
        self.assertTrue(proc._output_channel)
        self.assertEqual(slice(None, None), proc._pulse_slicer)
        self.assertEqual(0, proc._poi_index)
        self.assertEqual(1, proc.__class__._raw_ma.window)
        self.assertTupleEqual(default_bin_range, proc._bin_range)
        self.assertEqual(int(_DEFAULT_N_BINS), proc._n_bins)
        self.assertFalse(proc._hist_over_ma)

        # test set new values
        widget = ctrl_widget.output_ch_le
        widget.clear()
        QTest.keyClicks(widget, "new/output/channel")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual("new/output/channel", proc._output_channel)

        widget = ctrl_widget.pulse_slicer_le
        widget.clear()
        QTest.keyClicks(widget, "::2")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual(slice(None, None, 2), proc._pulse_slicer)

        widget = ctrl_widget.poi_index_le
        widget.clear()
        QTest.keyClicks(widget, "121")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual(0, proc._poi_index)  # maximum is 120 and one can still type "121"
        widget.clear()
        QTest.keyClicks(widget, "120")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual(120, proc._poi_index)

        widget = ctrl_widget.ma_window_le
        widget.clear()
        QTest.keyClicks(widget, "9")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual(9, proc.__class__._raw_ma.window)

        widget = ctrl_widget.bin_range_le
        widget.clear()
        QTest.keyClicks(widget, "-1.0, 1.0")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertTupleEqual((-1.0, 1.0), proc._bin_range)

        widget = ctrl_widget.n_bins_le
        widget.clear()
        QTest.keyClicks(widget, "1000")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual(100, proc._n_bins)  # maximum is 999 and one can not put the 3rd 0 in
        widget.clear()
        QTest.keyClicks(widget, "999")
        QTest.keyPress(widget, Qt.Key_Enter)
        self.assertEqual(999, proc._n_bins)

        ctrl_widget.hist_over_ma_cb.setChecked(True)
        self.assertTrue(proc._hist_over_ma)


class TestGotthardProcessor:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self._proc = GotthardProcessor(object(), object())

        self._proc._output_channel = "gotthard:output"
        self._adc = np.random.randint(0, 100, size=(4, 4), dtype=np.uint16)

    def _get_data(self, times=1):
        # data, meta
        return (
            {
                self._proc._output_channel: {
                    "metadata": {"timestamp.tid": 12345},
                    GotthardProcessor._DATA_PROPERTY: self._adc * times,
                    "data.3d": np.ones((4, 2, 2))
                },
            },
            {}
        )

    def testPreProcessing(self):
        proc = self._proc
        data = self._get_data()

        with pytest.raises(KeyError, match='false:output'):
            with patch.object(GotthardProcessor, "_output_channel",
                              new_callable=PropertyMock, create=True, return_value='false:output'):
                proc.process(data)

        with pytest.raises(ProcessingError, match="must contain property"):
            with patch.object(GotthardProcessor, "_DATA_PROPERTY",
                              new_callable=PropertyMock, return_value="false_ppt"):
                proc.process(data)

        with pytest.raises(ProcessingError, match="actual 3D"):
            with patch.object(GotthardProcessor, "_DATA_PROPERTY",
                              new_callable=PropertyMock, return_value="data.3d"):
                proc.process(data)

        with pytest.raises(ProcessingError, match="out of boundary"):
            proc._poi_index = 100
            processed = proc.process(data)
            assert processed is None
        # test not raise
        proc._poi_index = 3
        proc.process(data)
        with pytest.raises(ProcessingError, match="out of boundary"):
            # test with slicer
            proc._pulse_slicer = slice(None, None, 2)
            proc.process(data)

    @patch("extra_foam.special_suite.special_analysis_base.QThreadWorker._loadRunDirectory")
    def testLoadDarkRun(self, load_run):
        proc = self._proc

        load_run.return_value = None
        # nothing should happen
        proc.onLoadDarkRun("run/path")

        data_collection = MagicMock()
        load_run.return_value = data_collection
        with patch.object(proc.log, "error") as error:
            # get_array returns a wrong shape
            data_collection.get_array.return_value = DataArray(np.random.randn(4, 3))
            proc.onLoadDarkRun("run/path")
            error.assert_called_once()
            error.reset_mock()

            # get_array returns a correct shape
            data_collection.get_array.return_value = DataArray(np.random.randn(4, 3, 2))
            with patch.object(proc.log, "info") as info:
                proc.onLoadDarkRun("run/path")
                info.assert_called_once()
                error.assert_not_called()

    def testProcessingWhenRecordingDark(self):
        from extra_foam.special_suite.gotthard_proc import _PIXEL_DTYPE

        proc = self._proc
        assert 2147483647 == proc.__class__._dark_ma.window
        proc._recording_dark = True
        proc._subtract_dark = True  # take no effect
        proc._poi_index = 0

        adc_gt = self._adc.astype(_PIXEL_DTYPE)
        adc_gt2 = 2.0 * self._adc
        adc_gt_avg = 1.5 * self._adc

        # 1st train
        processed = proc.process(self._get_data())
        np.testing.assert_array_almost_equal(adc_gt, proc._dark_ma)
        np.testing.assert_array_almost_equal(np.mean(adc_gt, axis=0), proc._dark_mean_ma)
        assert 0 == processed["poi_index"]
        np.testing.assert_array_almost_equal(adc_gt, processed["displayed"])
        np.testing.assert_array_almost_equal(adc_gt, processed["displayed_ma"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt, axis=0), processed["mean"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt, axis=0), processed["mean_ma"])
        assert np.mean(adc_gt) == processed["hist"][2]

        # 2nd train
        processed = proc.process(self._get_data(2))
        np.testing.assert_array_almost_equal(adc_gt_avg, proc._dark_ma)
        np.testing.assert_array_almost_equal(np.mean(adc_gt_avg, axis=0), proc._dark_mean_ma)
        assert 0 == processed["poi_index"]
        np.testing.assert_array_almost_equal(adc_gt2, processed["displayed"])
        np.testing.assert_array_almost_equal(adc_gt_avg, processed["displayed_ma"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt2, axis=0), processed["mean"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt_avg, axis=0), processed["mean_ma"])
        assert np.mean(adc_gt2) == processed["hist"][2]

        # 3nd train
        proc._hist_over_ma = True
        processed = proc.process(self._get_data(3))
        np.testing.assert_array_almost_equal(adc_gt2, proc._dark_ma)
        np.testing.assert_array_almost_equal(np.mean(adc_gt2, axis=0), proc._dark_mean_ma)
        assert np.mean(adc_gt2) == processed["hist"][2]

    @pytest.mark.parametrize("subtract_dark", [(True, ), (False,)])
    def testProcessing(self, subtract_dark):
        from extra_foam.special_suite.gotthard_proc import _PIXEL_DTYPE

        proc = self._proc
        proc._recording_dark = False
        proc._poi_index = 1

        proc._subtract_dark = subtract_dark
        offset = np.ones(self._adc.shape[1]).astype(np.float32)
        proc._dark_mean_ma = offset
        proc._hist_over_ma = False

        adc_gt = self._adc.astype(_PIXEL_DTYPE)
        adc_gt2 = 2.0 * self._adc
        adc_gt_avg = 1.5 * self._adc
        if subtract_dark:
            adc_gt -= offset
            adc_gt2 -= offset
            adc_gt_avg -= offset

        # 1st train
        processed = proc.process(self._get_data())
        assert 1 == processed["poi_index"]
        np.testing.assert_array_almost_equal(adc_gt, processed["displayed"])
        np.testing.assert_array_almost_equal(adc_gt, processed["displayed_ma"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt, axis=0), processed["mean"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt, axis=0), processed["mean_ma"])
        assert np.mean(adc_gt) == processed["hist"][2]

        # 2nd train
        proc._setMaWindow(3)
        processed = proc.process(self._get_data(2))
        assert 1 == processed["poi_index"]
        np.testing.assert_array_almost_equal(adc_gt2, processed["displayed"])
        np.testing.assert_array_almost_equal(adc_gt_avg, processed["displayed_ma"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt2, axis=0), processed["mean"])
        np.testing.assert_array_almost_equal(np.mean(adc_gt_avg, axis=0), processed["mean_ma"])
        assert np.mean(adc_gt2) == processed["hist"][2]

        # 3nd train
        proc._hist_over_ma = True
        processed = proc.process(self._get_data(3))
        assert np.mean(adc_gt2) == processed["hist"][2]

    def testPulseSlicerChange(self):
        proc = self._proc

        del proc._dark_ma
        proc._dark_mean_ma = None
        proc._pulse_slicer = slice(None, None)

        proc.onPulseSlicerChanged([None, 4])
        assert proc._dark_mean_ma is None

        proc._dark_ma = np.random.randn(4, 2)
        proc.onPulseSlicerChanged([None, None, 2])
        # test _dark_mean_ma was re-calculated
        np.testing.assert_array_almost_equal(np.mean(proc._dark_ma[::2], axis=0), proc._dark_mean_ma)

    def testRemoveDark(self):
        proc = self._proc
        proc._dark_ma = np.ones((2, 2))
        proc._dark_mean_ma = np.ones((2, 2))

        proc.onRemoveDark()
        assert proc._dark_ma is None
        assert proc._dark_mean_ma is None
