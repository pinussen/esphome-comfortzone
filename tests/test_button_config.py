import importlib
from pathlib import Path
import unittest

try:
    import esphome.components
    import esphome.config_validation as cv
    from esphome.core import CORE
    esphome.components.__path__.append(str(Path(__file__).resolve().parents[1]/'components'))
    module = importlib.import_module('esphome.components.comfortzone.button')
except ImportError:
    module = None


@unittest.skipIf(module is None, 'Run with the ESPHome Python environment')
class ButtonConfigTest(unittest.TestCase):
    def validate(self, config):
        CORE.reset()
        return module.CONFIG_SCHEMA(config)

    def test_legacy_button(self):
        config=self.validate({'name':'Water','enable':True})
        self.assertEqual(config['action'],'extra_hot_water')
        self.assertEqual(config['icon'],'mdi:water-boiler')

    def test_fireplace(self):
        for enabled in [True,False]:
            self.assertEqual(self.validate({'name':'Fire','action':'fireplace','enable':enabled})['enable'],enabled)

    def test_clock(self):
        self.assertEqual(self.validate({'name':'Clock','action':'sync_clock','time_id':'sntp_time'})['action'],'sync_clock')

    def test_invalid_combinations(self):
        for extra in [{'action':'sync_clock'}, {'action':'sync_clock','enable':True,'time_id':'sntp_time'},
                      {'action':'fireplace'}, {'enable':True,'time_id':'sntp_time'}, {'action':'made_up'}]:
            with self.subTest(config=extra), self.assertRaises(cv.Invalid):
                self.validate({'name':'Invalid',**extra})
