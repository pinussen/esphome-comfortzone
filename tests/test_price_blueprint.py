"""Offline policy checks; not a substitute for loading the blueprint in HA."""
import math
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment

class Loader(yaml.SafeLoader):
    pass
Loader.add_constructor('!input', lambda loader,node: loader.construct_scalar(node))
BLUEPRINT=yaml.load((Path(__file__).resolve().parents[1]/'blueprints/automation/comfortzone_price_setback.yaml').read_text(),Loader=Loader)

class PriceBlueprintTest(unittest.TestCase):
    def evaluate(self, enabled='on', expensive='on', indoor='22', current=29.1, **overrides):
        states={'input_boolean.enabled':enabled,'binary_sensor.expensive':expensive,'sensor.indoor':indoor,'climate.heating':'heat'}
        attrs={'temperature':current,'min_temp':10,'max_temp':50}
        def number(v):
            try:return math.isfinite(float(v))
            except (ValueError,TypeError):return False
        env=Environment()
        env.globals.update(states=lambda k:states[k],is_state=lambda k,v:states[k]==v,
                           is_number=number,has_value=lambda k:states[k] not in ('unknown','unavailable'),
                           state_attr=lambda k,v:attrs.get(v))
        variables=dict(enabled='input_boolean.enabled',expensive='binary_sensor.expensive',indoor='sensor.indoor',
                       heating='climate.heating',normal=29.1,setback=27,minimum_indoor=21,trigger={'id':'price_changed','from_state':{'state':'on'}})
        variables.update(overrides)
        desired=float(env.from_string(BLUEPRINT['actions'][0]['variables']['desired']).render(**variables))
        variables['desired']=desired
        write=all(env.from_string(t).render(**variables).strip()=='True' for t in
                  [c['value_template'] for c in BLUEPRINT['conditions']]+[BLUEPRINT['actions'][1]['value_template']])
        return desired,write

    def test_expensive_and_comfortable(self):
        self.assertEqual(self.evaluate(),(27,True))

    def test_cheap_disabled_cold_or_unknown_returns_normal(self):
        for kw in [dict(expensive='off'),dict(enabled='off'),dict(indoor='20.5'),
                   dict(indoor='unavailable'),dict(expensive='unavailable'),dict(indoor='nan')]:
            with self.subTest(kw=kw):self.assertEqual(self.evaluate(**kw),(29.1,False))

    def test_matching_readback_does_not_write(self):
        self.assertEqual(self.evaluate(current=27),(27,False))

    def test_normal_restore_when_lowered(self):
        self.assertEqual(self.evaluate(current=27,enabled='off',trigger={'id':'enable_changed','from_state':{'state':'on'}}),(29.1,True))

    def test_invalid_bounds_or_missing_readback_prevent_write(self):
        for kw in [dict(setback=35),dict(normal=55,setback=55),dict(current=None)]:
            with self.subTest(kw=kw):self.assertFalse(self.evaluate(**kw)[1])

    def test_disabled_automation_does_not_overwrite_manual_target(self):
        self.assertEqual(self.evaluate(current=30,enabled='off'),(29.1,False))
