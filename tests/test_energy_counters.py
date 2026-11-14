import unittest
from energy_counters_v170 import Accumulator, report
from test_register_coverage import reply


def counters(c, a=0, w=0, source=b'\x65\x6f\xde\x02'):
    return reply(5,0x2c,b''.join(int(v).to_bytes(4,'little') for v in (c,a,w)),source=source)


def power(inp=1000, out=3000, heater=0):
    data=bytearray(58)
    for addr,value in [(0x2e9,300),(0x313,out),(0x315,heater),(0x319,out+heater),(0x321,inp)]:
        offset=addr-0x2e9
        data[offset:offset+2]=value.to_bytes(2,'little')
    return reply(1,0x2e9,data)


class EnergyCountersTest(unittest.TestCase):
    def test_matching_time_boundaries_and_repeated_counters(self):
        stream=[(0,power()),(1,counters(1000)),(5,counters(1000)),
                (10,power()),(20,counters(1002))]
        e=report(stream,window_s=19)['endpoints'][0]
        w=e['windows'][0]
        self.assertEqual(w['duration_s'],19)
        self.assertAlmostEqual(w['counter_delta_kwh']['compressor'],.02)
        self.assertAlmostEqual(w['integrated_kwh']['input'],1000*19/3600000)
        self.assertAlmostEqual(w['integrated_kwh']['output'],3000*19/3600000)
        self.assertEqual(w['coverage'],1)

    def test_missing_data_is_not_integrated_across_gap(self):
        a=Accumulator(45)
        a.power(0,[1000]*6)
        a.advance(100)
        self.assertEqual(a.coverage,45)
        self.assertAlmostEqual(a.energy[0],.0125)
        a.power(101,[0]*6)
        a.advance(110)
        self.assertEqual(a.coverage,54)
        self.assertAlmostEqual(a.energy[0],.0125)
        with self.assertRaises(ValueError):
            a.advance(109)

    def test_counter_reset_and_other_source_do_not_create_energy(self):
        e=report([(0,power()),(1,counters(100)),(2,counters(900,source=b'ABCD')),
                  (10,counters(1)),(20,counters(2))],window_s=10)['endpoints'][0]
        self.assertEqual(e['resets'],1)
        self.assertIsNone(e['whole_capture'])
        self.assertEqual(len(e['windows']),1)
        self.assertAlmostEqual(e['windows'][0]['counter_delta_kwh']['compressor'],.01)

    def test_water_pairing_crc_and_invalid_power(self):
        bad=bytearray(power());bad[-1]^=1
        stream=[(0,reply(1,0x17,bytes.fromhex('282e000010'))),
                (.5,power()),(1,counters(100)),(2,bytes(bad)),
                (10,power()),(11,power(inp=65535)),(20,counters(102))]
        e=report(stream,window_s=19)['endpoints'][0]
        w=e['windows'][0]
        self.assertEqual(e['power_samples'],2)
        self.assertAlmostEqual(w['integrated_kwh']['water_input'],1000*9/3600000)
        self.assertAlmostEqual(w['integrated_kwh']['input'],1000*10/3600000)
        self.assertAlmostEqual(w['coverage'],10/19)

    def test_heater_only_water_is_an_explicit_candidate(self):
        e=report([(0,reply(1,0x17,bytes.fromhex('230e000010'))),
            (0,power(inp=0,out=0,heater=6000)),(0,counters(100,100,100)),
            (6,counters(100,101,101))],window_s=6)['endpoints'][0]
        w=e['windows'][0]
        self.assertAlmostEqual(w['integrated_kwh']['water_heater_candidate'],.01)
        self.assertEqual(w['integrated_kwh']['water_output_recent'],0)
        scores=e['comparisons']['coverage_at_least_98pct']['scores']
        self.assertAlmostEqual(scores['additional_vs_heater']['mean_absolute_error_kwh'],0)
        self.assertAlmostEqual(scores['water_vs_heat']['mean_absolute_error_kwh'],0)


if __name__=='__main__':
    unittest.main()
