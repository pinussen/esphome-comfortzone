#!/usr/bin/env python3
"""Bounded passive API/UDP capture. Never sends a pump register write.

Requires aioesphomeapi and PyYAML from the ESPHome environment. Diagnostic UDP
forwarding is renewed with a short lease; loss of this process stops forwarding
within 120 seconds. PCAP timestamps are collector receipt times, not bus times.
"""
import argparse
import asyncio
import json
import math
from pathlib import Path
import signal
import shutil
import socket
import struct
import time


class DiskBudget:
    """Reserve space for the final status; stop all bulk writes at the limit."""
    def __init__(self, path, max_bytes, min_free_bytes):
        self.path, self.limit, self.min_free = path, max_bytes-65536, min_free_bytes
        self.used = 24
        self.checked = None
        self.reason = None

    def allow(self, size):
        if self.reason:
            return False
        if self.used+size > self.limit:
            self.reason = 'capture_size_limit'
            return False
        now = time.monotonic()
        if self.checked is None or now-self.checked >= 1:
            self.checked = now
            if shutil.disk_usage(self.path).free < self.min_free:
                self.reason = 'free_disk_space_limit'
                return False
        self.used += size
        return True


def udp_record(data, source, destination, source_port, port, now):
    udp = struct.pack('!HHHH', source_port, port, len(data)+8, 0)+data
    ip = bytearray(struct.pack('!BBHHHBBH4s4s', 0x45, 0, len(udp)+20, 0, 0, 64, 17, 0,
                               socket.inet_aton(source), socket.inet_aton(destination)))
    checksum = sum(struct.unpack('!10H', ip))
    while checksum >> 16:
        checksum = (checksum & 65535)+(checksum >> 16)
    struct.pack_into('!H', ip, 10, checksum ^ 65535)
    frame = bytes(12)+b'\x08\x00'+ip+udp
    return struct.pack('<IIII', int(now), int(now % 1*1e6), len(frame), len(frame))+frame


async def monitor(args):
    import yaml
    from aioesphomeapi import APIClient, LogLevel
    key = yaml.safe_load(args.secrets.read_text())['api_key']
    args.output.mkdir(parents=True, exist_ok=False)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    deadline = time.monotonic()+args.hours*3600
    started = time.time()
    count = 0
    last_packet = None
    connections = 0
    states = {}
    budget = DiskBudget(args.output, args.max_mib*1024**2, args.min_free_mib*1024**2)
    f = (args.output/'capture.pcap').open('wb')
    f.write(struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))
    events = (args.output/'events.jsonl').open('w', buffering=1)
    logs = (args.output/'device.jsonl').open('w', buffering=1)

    def write(stream, data):
        if budget.allow(len(data.encode('utf-8')) if isinstance(data, str) else len(data)):
            stream.write(data)
            return True
        stop.set()
        return False

    def event(kind, **values):
        write(events, json.dumps(dict(time=time.time(), kind=kind, **values), allow_nan=False)+'\n')

    def checkpoint(phase, connected=False):
        tmp = args.output/'status.tmp'
        tmp.write_text(json.dumps(dict(phase=phase, started=started, updated=time.time(),
                                      duration_hours=args.hours, connected=connected,
                                      max_mib=args.max_mib, min_free_mib=args.min_free_mib,
                                      stop_reason=budget.reason,
                                      connections=connections, packets=count,
                                      last_packet=last_packet, states=states), indent=2)+'\n')
        tmp.replace(args.output/'status.json')
        f.flush()

    class Receiver(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            nonlocal count, last_packet
            if addr[0] != args.host:
                return
            last_packet = time.time()
            if write(f, udp_record(data, addr[0], args.listen, addr[1], args.port, last_packet)):
                count += 1

    transport = None
    try:
        transport, _ = await loop.create_datagram_endpoint(Receiver, local_addr=(args.listen, args.port))
        event('start', host=args.host, expected_mac=args.mac, hours=args.hours,
              note='UDP forwarding only; no pump writes. API subscription can affect no-client reboot timers.')
        while not stop.is_set() and time.monotonic() < deadline:
            c = APIClient(args.host, 6053, noise_psk=key, provide_time=False)
            reroute = None
            try:
                await asyncio.wait_for(c.connect(login=True), 25)
                info = await asyncio.wait_for(c.device_info(), 15)
                if info.mac_address.lower() != args.mac.lower():
                    event('identity_mismatch', actual=info.mac_address)
                    raise SystemExit('Unexpected device MAC; capture stopped')
                entities, services = await asyncio.wait_for(c.list_entities_services(), 15)
                names = {e.key: e.name for e in entities}
                states.clear()
                connections += 1
                event('connected', build=info.compilation_time, mac=info.mac_address)

                def state(s):
                    if not hasattr(s, 'state'):
                        return
                    value = s.state
                    if isinstance(value, float) and not math.isfinite(value):
                        value = None
                    name = names.get(s.key, str(s.key))
                    # Missing binary/sensor state is unknown, not false/zero.
                    if getattr(s, 'missing_state', False):
                        value = None
                    states[name] = value
                    event('state', key=s.key, name=name, value=value)

                def log(m):
                    msg = m.message.decode(errors='replace') if isinstance(m.message, bytes) else str(m.message)
                    write(logs, json.dumps(dict(time=time.time(), message=msg))+'\n')

                c.subscribe_states(state)
                c.subscribe_logs(log, log_level=LogLevel.LOG_LEVEL_INFO, dump_config=True)
                reroute = next(s for s in services if s.name == 'debug_reroute')
                while c.is_connected and not stop.is_set() and time.monotonic() < deadline:
                    await asyncio.wait_for(c.execute_service(reroute, dict(ip=args.listen, port=float(args.port), timeout=120.)), 10)
                    event('forwarding_lease', seconds=120)
                    checkpoint('running', True)
                    try:
                        await asyncio.wait_for(stop.wait(), min(60, max(.01, deadline-time.monotonic())))
                    except asyncio.TimeoutError:
                        pass
                event('session_end', connected=c.is_connected)
            except Exception as exc:
                # Exception class suffices for diagnostics; do not log credentials.
                event('connection_error', error_type=type(exc).__name__)
            finally:
                if reroute and c.is_connected:
                    try:
                        await asyncio.wait_for(c.execute_service(reroute, dict(ip=args.listen, port=float(args.port), timeout=1.)), 5)
                    except Exception:
                        pass
                await c.disconnect()
                checkpoint('reconnecting')
            if not stop.is_set() and time.monotonic() < deadline:
                try:
                    await asyncio.wait_for(stop.wait(), min(10, deadline-time.monotonic()))
                except asyncio.TimeoutError:
                    pass
        event('finished', packets=count)
    finally:
        if transport:
            transport.close()
        checkpoint('stopped')
        f.close()
        events.close()
        logs.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', required=True)
    p.add_argument('--mac', required=True)
    p.add_argument('--listen', required=True, help='Collector IPv4 reachable from device')
    p.add_argument('--port', type=int, default=19502)
    p.add_argument('--hours', type=float, default=24)
    p.add_argument('--max-mib', type=int, default=128, help='Total bulk output limit, MiB')
    p.add_argument('--min-free-mib', type=int, default=2048, help='Stop below this free disk space')
    p.add_argument('--secrets', type=Path, default=Path('secrets.yaml'))
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.max_mib < 1 or args.min_free_mib < 1:
        p.error('Disk limits must be positive')
    if not 0 < args.hours <= 72 or not 1 <= args.port <= 65535:
        p.error('hours must be >0 and <=72; port must be 1..65535')
    for address in (args.host, args.listen):
        socket.inet_aton(address)
    asyncio.run(monitor(args))
