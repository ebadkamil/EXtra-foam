import unittest
from unittest.mock import MagicMock
import tempfile

import numpy as np

from karaboFAI.services import FaiServer
from karaboFAI.gui.plot_widgets.image_view import (
    ImageAnalysis, PumpProbeImageView
)
from karaboFAI.pipeline.data_model import ImageData
from karaboFAI.logger import logger
from karaboFAI.config import config


class TestImageAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FaiServer()

        config["PIXEL_SIZE"] = 1e-6
        config["MASK_RANGE"] = (None, None)

        cls._widget = ImageAnalysis(color_map="thermal")

    def testSaveLoadImageMask(self):
        fp = tempfile.TemporaryFile()
        # if image_data is None, it does not raise but only logger.error()
        with self.assertLogs(logger, level="ERROR"):
            self._widget._saveImageMaskImp(fp)

        with self.assertLogs(logger, level="ERROR") as cm:
            self._widget._loadImageMaskImp(fp)
        self.assertEqual(cm.output[0].split(':')[-1],
                         'Cannot load image mask without image!')

        imgs = np.arange(100, dtype=np.float).reshape(10, 10)
        mask = np.zeros_like(imgs, dtype=bool)
        self._widget.setImageData(ImageData(imgs))

        # the IOError
        with self.assertLogs(logger, level="ERROR") as cm:
            self._widget._loadImageMaskImp('abc')
        self.assertEqual(cm.output[0].split(':')[-1],
                         'Cannot load mask from abc')

        self._widget._saveImageMaskImp(fp)

        fp.seek(0)
        self._widget._loadImageMaskImp(fp)
        # the change of 'image_mask' will only reflect on the new instance
        # of ImageData
        np.testing.assert_array_equal(mask,
                                      ImageData(imgs).image_mask)

        # save and load another mask
        mask[0, 0] = 1
        mask[5, 5] = 1
        mask_item = self._widget._mask_item
        mask_item._mask.setPixelColor(0, 0, mask_item._OPAQUE)
        mask_item._mask.setPixelColor(5, 5, mask_item._OPAQUE)
        fp.seek(0)
        self._widget._saveImageMaskImp(fp)
        fp.seek(0)
        self._widget._loadImageMaskImp(fp)

        np.testing.assert_array_equal(mask,
                                      ImageData(imgs).image_mask)

        # load a mask with different shape
        new_mask = np.array((3, 3), dtype=bool)
        fp.seek(0)
        np.save(fp, new_mask)
        fp.seek(0)
        with self.assertLogs(logger, level='ERROR'):
            self._widget._loadImageMaskImp(fp)

        np.testing.assert_array_equal(mask,
                                      ImageData(imgs).image_mask)


class TestPumpProbeImageView(unittest.TestCase):
    class Data:
        class PP:
            def __init__(self):
                self.frame_rate = 1
                self.on_image_mean = None
                self.off_image_mean = None

        def __init__(self):
            self.pp = self.PP()

    @classmethod
    def setUpClass(cls):
        config["COLOR_MAP"] = "thermal"

    def testPumpProbeOnOffWidgetFrameRate1(self):
        data = self.Data()
        widget = PumpProbeImageView(on=True)
        widget.setImage = MagicMock()
        widget.updateROI = MagicMock()
        func = widget.setImage

        # no data
        widget.update(data)
        self.assertFalse(func.called)

        img = np.arange(4).reshape(2, 2)

        # data comes
        data.pp.on_image_mean = img
        widget.update(data)
        func.assert_called()
        func.reset_mock()

        # no data
        data.pp.on_image_mean = None
        widget.update(data)
        self.assertFalse(func.called)

    def testPumpProbeOnOffWidgetFrameRate2(self):
        data = self.Data()
        data.pp.frame_rate = 2
        widget = PumpProbeImageView(on=False)
        widget.setImage = MagicMock()
        widget.updateROI = MagicMock()
        func = widget.setImage

        img = np.arange(4).reshape(2, 2)

        # data comes
        data.pp.off_image_mean = img
        widget.update(data)
        func.assert_called()
        func.reset_mock()

        # no data, use cached data
        data.pp.off_image_mean = None
        widget.update(data)
        func.assert_called()
        func.reset_mock()

        # still no data
        data.pp.data = None
        widget.update(data)
        self.assertFalse(func.called)
        self.assertIs(widget._cached_image, None)  # cached data should be reset
