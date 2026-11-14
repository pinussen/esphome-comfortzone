#!/usr/bin/env python3
"""Offline search for monotone numeric fields correlated with electrical input.

Scan complete fields at every byte offset, both endian orders, without joining
different frames, banks or endpoints. Downsample range observations to control
cost; decreases are therefore only those seen at the sampled resolution.
Correlation is a candidate ranking, never proof of a register's meaning.
"""
import argparse
from collections import Counter
from functools import lru_cache
import json
import math
from pathlib import Path
import struct
from pcap_decode_v170 import Frame, PREFIX, packets, valid_frame
from energy_counters_v170 import Accumulator

FEATURES = ('input_kwh','output_kwh','heater_kwh','running_hours','elapsed_hours')
FORMATS = [(f'u{size*8}{order}',size,order,None)
           for size in (2,3,4,8) for order in ('little','big')]
FORMATS += [(f'f{size*8}{order}',size,order,('<' if order=='little' else '>')+code)
            for size,code in ((4,'f'),(8,'d')) for order in ('little','big')]


class Candidate:
    def __init__(self, time, value, energy, coverage):
        self.first_time = self.last_time = time
        self.first = self.last = value
        self.samples = 1
        self.increases = self.decreases = 0
        self.start = (time,value,energy.copy(),coverage)
        self.n = 0
        self.yy = self.sum_y = 0.
        self.xx = [0.]*len(FEATURES)
        self.xy = [0.]*len(FEATURES)

    def add(self,time,value,energy,coverage,window_s):
        self.samples += 1
        self.increases += value > self.last
        self.decreases += value < self.last
        self.last_time,self.last = time,value
        if value < self.start[1]:
            self.start = (time,value,energy.copy(),coverage)
            return
        elapsed = time-self.start[0]
        if elapsed < window_s:
            return
        if (coverage-self.start[3])/elapsed >= .98:
            y = value-self.start[1]
            x = [b-a for a,b in zip(self.start[2],energy)]
            self.n += 1
            self.yy += y*y
            self.sum_y += y
            for i,v in enumerate(x):
                self.xx[i] += v*v
                self.xy[i] += v*y
        self.start = (time,value,energy.copy(),coverage)

    def result(self):
        if self.n < 12 or self.increases < 12 or self.yy<=0:
            return None
        fits = {}
        for i,name in enumerate(FEATURES):
            if self.xx[i]<=0 or self.xy[i]<=0:
                continue
            slope = self.xy[i]/self.xx[i]
            # Relative RMS error for a through-origin fit of increments.
            error = math.sqrt(max(0., self.yy-self.xy[i]**2/self.xx[i])/self.yy)
            fits[name] = dict(raw_units_per_unit=slope, relative_rms_error=error)
        if 'input_kwh' not in fits:
            return None
        return dict(first=self.first,last=self.last,delta=self.last-self.first,
            samples=self.samples,increases=self.increases,decreases=self.decreases,
            windows=self.n,start=self.first_time,end=self.last_time,fits=fits)


def scan(stream,sample_s=60,window_s=1800):
    checked=lru_cache(maxsize=8192)(valid_frame)
    endpoints={}
    ranges={}
    fields={}
    counts=Counter()
    for time,raw in stream:
        counts['packets']+=1
        if not checked(raw) or raw[11:12]!=b'r' or raw[12:18]!=PREFIX:
            continue
        f=Frame(time,raw)
        if f.address+len(f.data)>65536:
            continue
        endpoint=f.device+':'+raw[:4].hex()
        if endpoint not in endpoints:
            endpoints[endpoint]=Accumulator(45)
        acc=endpoints[endpoint]
        acc.advance(time)
        if f.bank==1 and f.read(0x2e9,58) is not None:
            frequency,out,heater,inp=[int.from_bytes(f.read(a,2),'little') for a in (0x2e9,0x313,0x315,0x321)]
            if max(frequency,out,heater,inp)<=32767:
                # Accumulator divides by 3.6e6; 1000 produces elapsed hours.
                acc.power(time,[inp,out,heater,1000 if frequency else 0,1000])
            else:
                acc.power(time,None)
        range_key=(endpoint,f.bank,f.address,len(f.data))
        r=ranges.setdefault(range_key,dict(replies=0,sampled=0,last_sample=None))
        r['replies']+=1
        if r['last_sample'] is not None and time-r['last_sample']<sample_s:
            continue
        r['last_sample']=time
        r['sampled']+=1
        for offset in range(len(f.data)):
            for label,size,order,fmt in FORMATS:
                if offset+size>len(f.data):continue
                data=f.data[offset:offset+size]
                value=struct.unpack(fmt,data)[0] if fmt else int.from_bytes(data,order)
                if not math.isfinite(value) or value<0 or value>1e24:continue
                key=(endpoint,f.bank,f.address+offset,label)
                if key not in fields:
                    fields[key]=Candidate(time,value,acc.energy[:5],acc.coverage)
                else:
                    fields[key].add(time,value,acc.energy[:5],acc.coverage,window_s)
    candidates=[]
    for (endpoint,bank,address,encoding),field in fields.items():
        result=field.result()
        if result:
            candidates.append(dict(endpoint=endpoint,bank=bank,address=f'{address:04x}',encoding=encoding,**result))
    candidates.sort(key=lambda c:c['fits']['input_kwh']['relative_rms_error'])
    return dict(counts=dict(counts),sample_s=sample_s,window_s=window_s,fields_examined=len(fields),
        ranges=[dict(endpoint=k[0],bank=k[1],address=f'{k[2]:04x}',bytes=k[3],**r) for k,r in ranges.items()],
        candidates=candidates,
        caveat='Sampled monotonicity and fitted scale are hypotheses. Numeric aliases, runtime and output heat may correlate with input; inspect competing fits and raw evidence.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pcap',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sample-s',type=float,default=60)
    args=p.parse_args()
    if args.sample_s<=0:p.error('sample-s must be positive')
    r=scan(packets(args.pcap),args.sample_s)
    r['capture']=str(args.pcap)
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Fields:',r['fields_examined'],'Candidates:',len(r['candidates']))
    for c in r['candidates'][:25]:
        print(c['bank'],c['address'],c['encoding'],'down',c['decreases'],c['fits'])
