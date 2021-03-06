import unittest

from extra_foam.logger import logger_suite as logger
from extra_foam.gui import mkQApp
from extra_foam.special_suite.facade import _SpecialSuiteFacadeBase


app = mkQApp()

logger.setLevel('CRITICAL')


class TestFacade(unittest.TestCase):
    def _create_facade(self, n_analysis):
        window_isntance_types = []
        for i in range(n_analysis):
            if n_analysis == 2:
                window_isntance_types.append(type(f"DummyWindow{i}", (), {"_title": "title"}))
            else:
                window_isntance_types.append(type(f"DummyWindow{i}", (), {"_title": str(i)}))

        class SampleFacade(_SpecialSuiteFacadeBase):
            def __init__(self):
                super().__init__("DET")

                for i in range(n_analysis):
                    self.addSpecial("Gotthard.png", window_isntance_types[i])

                self.initUI()

        return SampleFacade

    def testGeneral(self):
        # test instantiation
        self._create_facade(9)()

        # test duplicated title
        with self.assertRaises(RuntimeError):
            self._create_facade(2)()
