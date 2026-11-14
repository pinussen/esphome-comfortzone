#!/usr/bin/env python3
"""Compare pump counter increments with integrated power over matched windows.

Offline, read-only; counter names are hypotheses, not electrical-energy labels.
No extrapolation beyond max_gap_s, no mixing of endpoints or counter resets.
"""
import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
from pcap_decode_v170 import Frame, PREFIX, packets, valid_frame

COUNTERS = ('compressor', 'additional', 'hot_water')
CHANNELS = ('input', 'output', 'heater', 'total', 'water_input', 'water_output',
            'water_input_recent', 'water_output_recent', 'water_heater_candidate')


class Accumulator:
    def __init__(self, max_gap_s):
        self.max_gap = max_gap_s
        self.time = self.power_time = None
        self.values = None
        self.energy = [0.] * len(CHANNELS)
        self.coverage = 0.

    def advance(self, now):
        if self.time is not None:
            if now < self.time:
                raise ValueError('Backwards capture timestamp')
            if self.values is not None:
                dt = max(0., min(now, self.power_time+self.max_gap)-self.time)
                self.coverage += dt
                for i, value in enumerate(self.values):
                    self.energy[i] += value*dt/3600000
        self.time = now

    def power(self, now, values):
        self.advance(now)
        self.power_time, self.values = now, values

    def snapshot(self, now, counters):
        self.advance(now)
        return dict(time=now, counters=counters, energy=self.energy.copy(), coverage=self.coverage)


def window(start, end):
    duration = end['time']-start['time']
    return dict(start=start['time'], end=end['time'], duration_s=duration,
                coverage=(end['coverage']-start['coverage'])/duration,
                counter_delta_kwh=dict(zip(COUNTERS, [b-a for a,b in zip(start['counters'],end['counters'])])),
                integrated_kwh=dict(zip(CHANNELS, [b-a for a,b in zip(start['energy'],end['energy'])])))


def comparisons(windows):
    """Quantify competing interpretations, including heater-only water windows."""
    usable = [w for w in windows if w['coverage'] >= .98]
    groups = {
        'coverage_at_least_98pct': usable,
        'water_dominant': [w for w in usable if w['integrated_kwh']['water_output_recent'] > .05
            and w['integrated_kwh']['water_output_recent'] >= .95*w['integrated_kwh']['output']],
    }
    result = {}
    for name, rows in groups.items():
        if not rows:
            continue
        hypotheses = {'compressor_vs_input': ('compressor', ('input',)),
            'compressor_vs_output': ('compressor', ('output',)),
            'additional_vs_heater': ('additional', ('heater',)),
            'water_vs_electricity': ('hot_water', ('water_input_recent','water_heater_candidate')),
            'water_vs_heat': ('hot_water', ('water_output_recent','water_heater_candidate'))}
        scores = {}
        for hypothesis, (counter, channels) in hypotheses.items():
            measured = [w['counter_delta_kwh'][counter] for w in rows]
            integrated = [sum(w['integrated_kwh'][c] for c in channels) for w in rows]
            scores[hypothesis] = dict(counter_kwh=sum(measured), integral_kwh=sum(integrated),
                mean_absolute_error_kwh=sum(abs(a-b) for a,b in zip(measured,integrated))/len(rows))
        result[name] = dict(windows=len(rows), scores=scores)
    return result


def report(stream, window_s=1800, max_gap_s=45):
    endpoints = {}
    counts = Counter()
    checked = lru_cache(maxsize=8192)(valid_frame)
    for time, raw in stream:
        counts['packets'] += 1
        if not checked(raw) or raw[11:12] != b'r' or raw[12:18] != PREFIX:
            continue
        f = Frame(time, raw)
        if f.address+len(f.data)>65536:
            continue
        key = f.device+':'+raw[:4].hex()
        e = endpoints.setdefault(key, dict(acc=Accumulator(max_gap_s), status=None,
                first=None, last=None, start=None, windows=[], resets=0, power_samples=0, counter_samples=0))
        if f.bank == 1:
            status = f.read(0x17,5)
            if status is not None:
                e['status'] = (time, status)
            if f.read(0x2e9,0x323-0x2e9) is not None:
                output, heater, total, inp = [int.from_bytes(f.read(a,2),'little') for a in (0x313,0x315,0x319,0x321)]
                if max(output,heater,total,inp)>32767:
                    counts['invalid_power'] += 1
                    e['acc'].power(time,None)
                    continue
                previous = e['status']
                # Candidate water integrals only: no generic bit decoding.
                water = previous and 0 <= time-previous[0] <= 2 and previous[1][1] in (0x2c,0x2e)
                recent = previous and 0 <= time-previous[0] <= 45
                water_recent = recent and previous[1][1] in (0x2c,0x2e)
                # 0E is an offline heater-only water hypothesis. Report this
                # separately; it is not a verified production bit or HA state.
                water_heater = recent and previous[1][1] in (0x0e,0x2c,0x2e)
                e['acc'].power(time,[inp,output,heater,total,inp if water else 0,output if water else 0,
                    inp if water_recent else 0,output if water_recent else 0,heater if water_heater else 0])
                e['power_samples'] += 1
        elif f.bank == 5 and (data := f.read(0x2c,12)) is not None:
            values = [int.from_bytes(data[i:i+4],'little')/100 for i in (0,4,8)]
            snap = e['acc'].snapshot(time,values)
            e['counter_samples'] += 1
            if e['last'] and any(b<a for a,b in zip(e['last']['counters'],values)):
                e['resets'] += 1
                e['start'] = snap
            if e['first'] is None:
                e['first'] = e['start'] = snap
            if time-e['start']['time'] >= window_s:
                e['windows'].append(window(e['start'],snap))
                e['start'] = snap
            e['last'] = snap
    result = []
    for endpoint,e in endpoints.items():
        if not e['first'] or e['last']['time']<=e['first']['time']:
            continue
        result.append(dict(endpoint=endpoint, power_samples=e['power_samples'], counter_samples=e['counter_samples'],
            resets=e['resets'], first_counters_kwh=dict(zip(COUNTERS,e['first']['counters'])),
            last_counters_kwh=dict(zip(COUNTERS,e['last']['counters'])),
            whole_capture=window(e['first'],e['last']) if not e['resets'] else None,
            windows=e['windows'], comparisons=comparisons(e['windows'])))
    return dict(counts=dict(counts), window_s=window_s, max_gap_s=max_gap_s, endpoints=result,
                method='Left hold, bounded age; water_input/output require status <=2 s. Recent candidates use <=45 s and second byte 2C/2E; heater candidate also includes 0E. These hypotheses are not generic bit decoding. Counter resolution 0.01 kWh.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pcap',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window-s',type=float,default=1800)
    p.add_argument('--max-gap-s',type=float,default=45)
    args = p.parse_args()
    if args.window_s<=0 or args.max_gap_s<=0:
        p.error('Intervals must be positive')
    r=report(packets(args.pcap),args.window_s,args.max_gap_s)
    r['capture']=str(args.pcap)
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    for e in r['endpoints']:
        print(json.dumps({k:v for k,v in e.items() if k!='windows'},indent=2))
