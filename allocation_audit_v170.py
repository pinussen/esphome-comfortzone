#!/usr/bin/env python3
"""Offline audit of electricity excluded by protocol-170 allocation guards.

Mirrors the operating classifier at status/power events, integrating a left
hold between them. It does not reproduce ESPHome's one-second scheduling or
HA statistics exactly. A relaxed pairing result is a hypothesis, not firmware.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
from pcap_decode_v170 import Frame,PREFIX,packets,valid_frame


def profile(raw):
    if not raw or raw[2:]!=bytes((0,0,0x10)):return None
    first,second=raw[:2]
    if first==0x20 and second not in (8,0x2a):return None
    if first==0x30 and second!=0x2a:return None
    if first==0x23 and second not in (8,0x2a,0x2e):return None
    if first not in (0x20,0x23,0x28,0x2b,0x30):return None
    return {8:'idle',0x2a:'heating',0x2c:'hot_water',0x2e:'hot_water'}.get(second)


class Model:
    def __init__(self,age=45,pair_window=2,retain_pair=False):
        self.age,self.pair_window=age,pair_window
        self.retain_pair=retain_pair
        self.status=self.power=None
        self.status_time=self.power_time=self.time=None
        self.paired=False
        self.kwh=defaultdict(float)
        self.seconds=defaultdict(float)

    def reason(self,now):
        if self.power is None or now-self.power_time>self.age:return 'missing_power'
        freq,out,heater,total,inp=self.power
        if inp>32767:return 'invalid_input'
        if not any(self.power):return 'stopped'
        if self.status is None or now-self.status_time>self.age:return 'missing_status'
        if not self.paired:return 'pair_window'
        mode=profile(self.status)
        if mode not in ('heating','hot_water'):return 'unmapped_profile'
        if not 0<freq<=32767 or not 0<out<=32767 or not 0<inp<=32767 or max(total,heater)>32767:
            return 'invalid_production_snapshot'
        if heater:return 'heater_active'
        if total!=out:return 'output_total_mismatch'
        return mode

    def advance(self,now):
        if self.time is None:
            self.time=now;return
        if now<self.time:raise ValueError('Backwards timestamp')
        cuts=[self.time,now]
        for t in (self.status_time,self.power_time):
            if t is not None and self.time<t+self.age<now:cuts.append(t+self.age)
        cuts.sort()
        for a,b in zip(cuts,cuts[1:]):
            why=self.reason((a+b)/2)
            self.seconds[why]+=b-a
            if why not in ('missing_power','invalid_input'):
                self.kwh[why]+=self.power[4]*(b-a)/3600000
        self.time=now

    def update_status(self,now,raw):
        self.advance(now)
        if self.status is None or now-self.status_time>self.age or raw!=self.status:self.paired=False
        self.status,self.status_time=raw,now

    def update_power(self,now,power):
        self.advance(now)
        self.power,self.power_time=power,now
        self.paired=self.status is not None and now-self.status_time<=self.age and (
            now-self.status_time<=self.pair_window or (self.retain_pair and self.paired))

    def result(self):
        total=sum(self.kwh.values())
        allocated=self.kwh['heating']+self.kwh['hot_water']
        return dict(total_input_kwh=total,allocated_kwh=allocated,unallocated_kwh=total-allocated,
            allocated_fraction=allocated/total if total else None,
            kwh_by_reason=dict(self.kwh),seconds_by_reason=dict(self.seconds))


def audit(stream):
    checked=lru_cache(maxsize=8192)(valid_frame)
    endpoints={}
    for time,raw in stream:
        if not checked(raw) or raw[11:12]!=b'r' or raw[12:18]!=PREFIX:continue
        f=Frame(time,raw)
        if f.bank!=1 or f.address+len(f.data)>65536:continue
        status=f.read(0x17,5)
        power=f.read(0x2e9,58)
        if status is None and power is None:continue
        key=f.device+':'+raw[:4].hex()
        if key not in endpoints:
            endpoints[key]={'previous_15s':Model(15),'current_45s':Model(45),
                            'candidate_retain_pair':Model(45,2,True),
                            'candidate_pair_45s':Model(45,45)}
        for model in endpoints[key].values():
            if status is not None:model.update_status(time,status)
            if power is not None:
                model.update_power(time,[int.from_bytes(f.read(a,2),'little') for a in (0x2e9,0x313,0x315,0x319,0x321)])
    return {key:{name:model.result() for name,model in models.items()} for key,models in endpoints.items()}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pcap',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=dict(capture=str(args.pcap),endpoints=audit(packets(args.pcap)),
                caveat='Offline event-time left-hold approximation. No reconstruction across power expiry. Relaxed pairing has not been validated as a production rule.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
