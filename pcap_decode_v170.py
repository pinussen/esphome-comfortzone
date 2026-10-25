#!/usr/bin/env python3
"""Offline protocol-170 analysis: byte ranges, overlaps and dated records.

No device access or writes. Only complete CRC-valid replies enter the memory
map. Every capture is analysed separately; addresses from other protocols,
devices and memory banks are never merged. JSON includes provenance and age.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import statistics
import struct

PREFIX = bytes.fromhex("010203040b08")


def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8c if crc & 1 else 0)
    return crc


def packets(path):
    """Classic PCAP Ethernet/IPv4 UDP, both byte orders and time resolutions."""
    with Path(path).open('rb') as f:
        h = f.read(24)
        formats = {b'\xd4\xc3\xb2\xa1': ('<', 1e6),
                   b'\xa1\xb2\xc3\xd4': ('>', 1e6),
                   b'\x4d\x3c\xb2\xa1': ('<', 1e9),
                   b'\xa1\xb2\x3c\x4d': ('>', 1e9)}
        if len(h) != 24 or h[:4] not in formats:
            raise ValueError('Expected classic PCAP')
        order, scale = formats[h[:4]]
        if struct.unpack_from(order+'I', h, 20)[0] != 1:
            raise ValueError('Expected Ethernet link type')
        while h := f.read(16):
            if len(h) != 16:
                raise ValueError('Truncated packet header')
            sec, sub, length, _ = struct.unpack(order+'IIII', h)
            p = f.read(length)
            if len(p) != length:
                raise ValueError('Truncated packet')
            if len(p) < 42 or p[12:14] != b'\x08\x00' or p[14] >> 4 != 4 or p[23] != 17:
                continue
            ihl = (p[14] & 15)*4
            total = int.from_bytes(p[16:18], 'big')
            if ihl < 20 or total < ihl+8 or len(p) < 14+total:
                continue
            if int.from_bytes(p[20:22], 'big') & 0x3fff:  # fragmented IP
                continue
            off = 14+ihl
            size = int.from_bytes(p[off+4:off+6], 'big')
            if size < 8 or size > total-ihl:
                continue
            yield sec+sub/scale, p[off+8:off+size]


@dataclass(frozen=True)
class Frame:
    time: float
    raw: bytes

    @property
    def address(self):
        return int.from_bytes(self.raw[19:21], 'little')

    @property
    def data(self):
        return self.raw[21:-1]

    @property
    def bank(self):
        return self.raw[18]

    @property
    def reg(self):
        return self.raw[18:21].hex(' ')

    @property
    def device(self):
        return self.raw[6:10].hex()

    def read(self, address, size):
        off = address-self.address
        if 0 <= off and off+size <= len(self.data):
            return self.data[off:off+size]
        return None


def valid_frame(p):
    return (len(p) >= 22 and p[10] == len(p) and p[11] in b'RrWw'
            and crc8(p[:4]) == p[4]
            and crc8(bytes(b ^ 255 for b in p[:4])) == p[5]
            and crc8(p[:-1]) == p[-1])


def decode_fields(f):
    """Existing established mappings plus explicitly marked new candidates."""
    result = {}
    if f.bank == 0:
        for addr, name, scale, size in [(0x2a5, 'heating_curve', 1, 1),
                (0x2a6, 'heating_setting_c', 10, 2), (0x373, 'hot_water_setting_c', 10, 2),
                (0x419, 'filter_days', 1, 2), (0x3fa, 'fan_mode', 1, 1),
                (0x3d2, 'hot_water_max_runtime_minutes', 1, 1),
                (0x3d3, 'hot_water_pause_minutes', 1, 1),
                (0x3e4, 'hot_water_min_frequency_hz', 10, 2),
                (0x3e6, 'hot_water_max_frequency_hz', 10, 2),
                (0x3ec, 'extra_hot_water_target_c', 10, 2),
                (0x3ee, 'extra_hot_water_minutes', 1, 2),
                (0x3fb, 'normal_fan_percent', 10, 2)]:
            if (b := f.read(addr, size)) is not None:
                result[name] = int.from_bytes(b, 'little') / scale
    elif f.bank == 1:
        for index in [*range(8), 10, 24]:
            if (b := f.read(0x32+2*index, 2)) is not None:
                raw = int.from_bytes(b, 'little', signed=True)
                result[f'te{index}_c'] = None if raw in (-990, -999) else raw / 10
        if (b := f.read(4, 6)) is not None:
            hour, minute, second, day, month, year = b
            try:
                result['pump_datetime'] = datetime(2000+year, month, day, hour, minute, second).isoformat()
                if (weekday := f.read(10, 1)) is not None:
                    result['weekday_raw'] = weekday[0]
            except ValueError:
                result['invalid_clock_hex'] = b.hex()
        for address, name in [(0x1f, 'pending_alarm_mask'), (0x27, 'acknowledged_alarm_mask'),
                (0x2d5, 'compressor_frequency_raw'), (0x313, 'compressor_output_w'),
                (0x317, 'additional_power_w'), (0x319, 'total_output_w'), (0x321, 'compressor_input_w')]:
            if (b := f.read(address, 2)) is not None:
                result[name] = int.from_bytes(b, 'little')
        # 12 float32 values repeated in two neighbouring arrays. Sensor names
        # remain candidates: close numerical agreement does not prove semantics.
        for addr in (0xe1, 0x111):
            if (b := f.read(addr, 48)) is not None:
                vals = struct.unpack('<12f', b)
                result[f'candidate_float_temperatures_{addr:04x}'] = [
                    round(v/10, 5) if abs(v) < 1e6 else None for v in vals]
    elif f.bank == 5:
        for i, name in enumerate(('compressor_kwh', 'additional_kwh', 'hot_water_kwh',
                                  'compressor_runtime_minutes', 'total_runtime_minutes')):
            if (b := f.read(0x2c+4*i, 4)) is not None:
                result[name] = int.from_bytes(b, 'little') / (100 if i < 3 else 1)
    return result


def event_snapshot(latest, f, max_age=10):
    if f.bank != 3:
        return None
    # Contiguous log region: header byte + 30 records of 14 bytes + trailer.
    parts = [latest.get((f.device, 3, a)) for a in (0xd15, 0xdc7, 0xe79)]
    if any(p is None or not 0 <= f.time-p.time <= max_age for p in parts):
        return None
    if any(len(p.data) < size for p, size in zip(parts, (178, 178, 66))):
        return None
    # The third address is read both as a 66-byte and a 178-byte block.
    data = b''.join(p.data[:size] for p, size in zip(parts, (178, 178, 66)))
    rows = []
    for slot in range(30):
        b = data[1+14*slot:15+14*slot]
        day, month, year, hour, minute, second = b[:6]
        try:
            when = datetime(2000+year, month, day, hour, minute, second).isoformat()
        except ValueError:
            when = None
        rows.append({'slot': slot, 'datetime': when, 'state_raw': b[6],
                     'code_raw': b[7], 'extra_hex': b[8:].hex(), 'raw_hex': b.hex()})
    return {'device': f.device, 'capture_time': f.time, 'header_raw': data[0],
            'trailer_raw': data[-1], 'source_times': [p.time for p in parts],
            'interpretation': 'Dated event ring candidate; state/code meanings unverified',
            'records': rows}


def analyze(path):
    counts = Counter()
    byreg = defaultdict(list)
    latest = {}
    overlaps = defaultdict(Counter)
    fields = []
    events = {}
    previous = None
    times = []
    for t, p in packets(path):
        counts['udp_payloads'] += 1
        if not valid_frame(p):
            counts['invalid_or_non_frame'] += 1
            continue
        counts['valid_frames'] += 1
        if previous and p == previous.raw and 0 <= t-previous.time < .1:
            counts['consecutive_identical_within_100ms'] += 1
        previous = Frame(t, p)
        if p[12:18] != PREFIX:
            counts['other_protocol_frames'] += 1
            continue
        counts[chr(p[11])] += 1
        if p[11] != ord('r'):
            continue
        f = Frame(t, p)
        times.append(t)
        byreg[(f.device, f.reg)].append(f)
        for (device, bank, addr), other in latest.items():
            if device != f.device or bank != f.bank or addr == f.address or not 0 <= t-other.time <= 10:
                continue
            start = max(addr, f.address)
            end = min(addr+len(other.data), f.address+len(f.data))
            if end <= start:
                continue
            key = (f.device, f.bank, min(addr, f.address), max(addr, f.address), start, end)
            a, b = f.read(start, end-start), other.read(start, end-start)
            c = overlaps[key]
            c['comparisons'] += 1
            c['equal_bytes'] += sum(x == y for x, y in zip(a,b))
            c['compared_bytes'] += len(a)
            c['exact_matches'] += a == b
            c['nonzero_compared_bytes'] += sum(x != 0 or y != 0 for x,y in zip(a,b))
        latest[f.device, f.bank, f.address] = f
        if decoded := decode_fields(f):
            fields.append({'capture_time': t, 'device': f.device, 'register': f.reg, **decoded})
        if snapshot := event_snapshot(latest, f):
            fingerprint = (f.device, snapshot['header_raw'], tuple(r['raw_hex'] for r in snapshot['records']))
            events[fingerprint] = snapshot
    regs = []
    for (device, reg), frames in sorted(byreg.items()):
        intervals = [b.time-a.time for a,b in zip(frames,frames[1:]) if b.time-a.time > .1]
        regs.append({'device': device, 'register': reg, 'count': len(frames),
                     'data_lengths': sorted({len(f.data) for f in frames}),
                     'distinct_payloads': len({f.data for f in frames}),
                     'median_interval_seconds': round(statistics.median(intervals),3) if intervals else None,
                     'data_bytes': sum(len(f.data) for f in frames)})
    return {'capture': str(Path(path).resolve()), 'counts': dict(counts),
            'reply_duration_seconds': round(max(times)-min(times),3) if times else 0,
            'registers': regs,
            'overlaps': [{'device': d, 'bank': bank, 'bases': [hex(a),hex(b)],
                          'range_start': hex(s), 'range_end_exclusive': hex(e), **c}
                         for (d,bank,a,b,s,e),c in sorted(overlaps.items())],
            'decoded_fields': fields, 'event_snapshots': list(events.values()),
            'caveats': ['Identical payloads are not automatically retransmissions.',
                        '100ms metric detects rapid repeats, not their cause.',
                        'Overlap comparisons use replies at most 10 seconds apart, not atomic snapshots.',
                        'No memory-card presence information is inferred from traffic.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pcap', type=Path, nargs='+')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    results = [analyze(path) for path in a.pcap]
    a.output.write_text(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    for r in results:
        print(r['capture'], r['counts'], 'registers=',len(r['registers']),
              'overlaps=',len(r['overlaps']), 'event_snapshots=',len(r['event_snapshots']))


if __name__ == '__main__':
    main()
