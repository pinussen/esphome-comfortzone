import unittest
from scan_energy_counters_v170 import Candidate,scan
from allocation_audit_v170 import Model,audit
from test_energy_counters import power,counters
from test_register_coverage import reply


class CounterSearchTest(unittest.TestCase):
    def test_exact_counter_matches_input_not_runtime(self):
        c=Candidate(0,1000,[0]*5,0)
        energy=[0.]*5
        value=1000
        for i in range(1,15):
            x=1 if i%2 else 3
            energy=[energy[0]+x,energy[1]+2,energy[2],energy[3]+.5,energy[4]+.5]
            value+=100*x
            c.add(i*1800,value,energy,i*1800,1800)
        r=c.result()
        self.assertAlmostEqual(r['fits']['input_kwh']['raw_units_per_unit'],100)
        self.assertAlmostEqual(r['fits']['input_kwh']['relative_rms_error'],0)
        self.assertGreater(r['fits']['running_hours']['relative_rms_error'],.1)

    def test_counter_decrease_does_not_create_positive_window(self):
        c=Candidate(0,1000,[0]*5,0)
        c.add(1800,1,[1]*5,1800,1800)
        self.assertEqual(c.n,0)
        self.assertEqual(c.decreases,1)
        c.add(3600,101,[2]*5,3600,1800)
        self.assertEqual(c.n,1)
        self.assertEqual(c.sum_y,100)

    def test_scan_validates_crc_and_separates_sources(self):
        bad=bytearray(counters(100));bad[-1]^=1
        r=scan([(0,power()),(1,counters(100)),(2,bytes(bad)),
                (3,reply(5,0x2c,bytes(12),source=b'ABCD'))])
        self.assertEqual(sum(x['replies'] for x in r['ranges']),3)
        self.assertEqual(len({x['endpoint'] for x in r['ranges']}),2)
        self.assertEqual(r['candidates'],[])

    def test_full_scan_finds_an_unknown_electrical_counter(self):
        stream=[(0,power()),(0,reply(3,0x100,(2000).to_bytes(4,'little')))]
        count=2000
        for i in range(14):
            watts=1000 if i%2==0 else 3000
            for elapsed in range(0,1800,30):
                stream.append((i*1800+elapsed,power(inp=watts)))
            count+=50 if i%2==0 else 150
            stream.append(((i+1)*1800,reply(3,0x100,count.to_bytes(4,'little'))))
        r=scan(stream)
        candidate=next(c for c in r['candidates'] if c['bank']==3 and c['address']=='0100' and c['encoding']=='u32little')
        self.assertEqual(candidate['decreases'],0)
        self.assertAlmostEqual(candidate['fits']['input_kwh']['raw_units_per_unit'],100)
        self.assertAlmostEqual(candidate['fits']['input_kwh']['relative_rms_error'],0)
        self.assertGreater(candidate['fits']['elapsed_hours']['relative_rms_error'],.1)


class AllocationAuditTest(unittest.TestCase):
    def test_late_status_pair_loses_allocation_not_total(self):
        m=Model()
        m.update_status(0,bytes.fromhex('282a000010'))
        m.update_power(1,[300,2400,0,2400,1000])
        m.update_power(10,[300,2400,0,2400,1000])
        m.advance(20)
        r=m.result()
        self.assertAlmostEqual(r['total_input_kwh'],19/3600)
        self.assertAlmostEqual(r['allocated_kwh'],9/3600)
        self.assertAlmostEqual(r['kwh_by_reason']['pair_window'],10/3600)

    def test_expiry_and_changed_status_remain_unknown(self):
        m=Model()
        m.update_status(0,bytes.fromhex('282a000010'))
        m.update_power(1,[300,2400,0,2400,1000])
        m.advance(60)
        r=m.result()
        self.assertAlmostEqual(r['total_input_kwh'],45/3600)
        self.assertAlmostEqual(r['allocated_kwh'],44/3600)
        self.assertAlmostEqual(r['kwh_by_reason']['missing_status'],1/3600)
        m.update_status(61,bytes.fromhex('282e000010'))
        m.update_power(62,[300,2400,0,2400,1000])
        self.assertEqual(m.reason(62),'hot_water')
        m.update_status(63,bytes.fromhex('280a000010'))
        self.assertEqual(m.reason(63),'pair_window')
        m.update_power(64,[300,2400,0,2400,1000])
        self.assertEqual(m.reason(64),'unmapped_profile')

    def test_crc_replay_and_heater_guard(self):
        bad=bytearray(power());bad[-1]^=1
        stream=[(0,reply(1,0x17,bytes.fromhex('282e000010'))),
            (1,power(heater=500)),(5,bytes(bad)),(10,power())]
        r=audit(stream)['656fde02:41444452']['current_45s']
        self.assertAlmostEqual(r['kwh_by_reason']['heater_active'],9/3600)
        self.assertEqual(r['allocated_kwh'],0)

    def test_retention_requires_initial_pair_and_drops_changed_status(self):
        m=Model(retain_pair=True)
        m.update_status(0,bytes.fromhex('282a000010'))
        m.update_power(3,[300,2400,0,2400,1000])
        self.assertEqual(m.reason(3),'pair_window')
        m.update_status(4,bytes.fromhex('282a000010'))
        m.update_power(5,[300,2400,0,2400,1000])
        m.update_power(12,[300,2400,0,2400,1000])
        self.assertEqual(m.reason(12),'heating')
        m.update_status(13,bytes.fromhex('282e000010'))
        m.update_power(16,[300,2400,0,2400,1000])
        self.assertEqual(m.reason(16),'pair_window')


if __name__=='__main__':unittest.main()
