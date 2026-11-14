# EX50 protocol 170: electricity versus heat counters

Analysis 2026-11-14. These are accumulated counters, not daily totals. The
start/reset epoch is not verified: say "since commissioning or last reset",
not guaranteed lifetime totals. The panel values supplied by the user were
73,333.02 kWh (Comp energy), 6,642.99 kWh (Add energy), and 13,354.04 kWh
(HW energy), consistent with continuation of the captured counters.

## Findings and Home Assistant use

| Existing entity | Register | Capture-supported meaning | Electrical energy dashboard |
| --- | --- | --- | --- |
| Compressor energy | 05:002c, u32 / 100 | Accumulated compressor **heat output**, as estimated/reported by the pump | Do not use as compressor electricity |
| Additional energy | 05:0030, u32 / 100 | Accumulated electric-heater contribution; matches integrated heater watts | Suitable for heater consumption, subject to the pump's own accuracy |
| Hot water energy | 05:0034, u32 / 100 | Evidence supports accumulated **heat delivered to hot water**, including heater contribution | Do not use as hot-water electricity |

The three counters do **not** provide a verified persistent compressor
electricity counter. Dividing accumulated heat by a fixed COP would not fix
this: COP varies. A dedicated electricity meter remains the robust way to
cover compressor electricity during ESP32 downtime and auxiliary loads.

The existing Total Daily Input Energy is calculated in ESPHome from 01:0321
(compressor electrical input), not from 05:002c. The Heating/Water daily input
totals allocate only recognised observations and can therefore sum to less
than the input total. Counter semantics must not be changed just to eliminate
that difference. Existing entity IDs and firmware are unchanged by this analysis.

## Seven-day comparison

Source: `comfortzone-week-20261028-205459/data/capture.pcap`, from
2026-10-28 through 2026-11-04. 2,532,329 packets; 68,013 complete power replies
and 68,024 complete counter replies from endpoint `656fde02:41444452`.
There were no decreasing counter observations. The matched interval is
604,786.38 s; bounded power coverage is 99.7417%.

| Counter increase | Matching integrated power | Competing interpretation |
| --- | --- | --- |
| Comp energy: **275.48 kWh** | Compressor heat output: **273.490 kWh** | Compressor electricity: **101.420 kWh** |
| Add energy: **10.51 kWh** | Heater power: **10.516 kWh** | — |
| HW energy: **27.95 kWh** | Candidate water heat + heater: **26.860 kWh** | Candidate water electricity + heater: **14.991 kWh** |

There are 334 non-overlapping approximately 30-minute windows, 325 with at
least 98% power coverage. Mean absolute window error for Comp energy is
0.00730 kWh against heat output versus 0.51098 kWh against electrical input.
For Add energy versus heater power it is 0.00042 kWh.

Eight well-covered windows have at least 95% of compressor heat in the
water candidate mode, with at least 0.05 kWh water heat each. In those windows:

- HW counter increase: **8.36 kWh**.
- Integrated compressor water heat + heater: **8.330 kWh**.
- Integrated compressor water electricity + heater: **4.187 kWh**.
- Mean absolute window error against water heat: **0.00499 kWh**, comparable
  with the counters' 0.01 kWh resolution.

The whole-week water allocation is less complete than the total power
coverage: missing/unrecognised status can lose allocation even when power is
available. The approximately 1.09 kWh difference is not filled by scaling or
guessing. The result supports the energy type and inclusion of heater heat;
it is not a complete proof of every transition/profile or physical accuracy.

The independent panel-session capture on 2026-11-14 also supports the result:
Comp energy increased 0.27 kWh versus integrated heat 0.267 kWh and input
0.120 kWh. Add energy increased 0.02 kWh versus integrated heater 0.0217 kWh.

## Method and reproducibility

`energy_counters_v170.py` accepts only complete CRC-valid protocol-170 replies,
separates source/destination pairs, matches integrals to counter timestamps,
rejects out-of-range power, and splits windows at decreasing counters. It
uses a left hold for at most 45 seconds, reports coverage, and never scales
the integral up to compensate for missing traffic. This is comparison of
the pump's own telemetry, not calibration against an independent meter.

The strict water candidates require status within 2 seconds of power. The
separate recent candidates allow 45 seconds and status second byte 2C/2E.
The heater-water hypothesis also includes 0E. These are explicitly offline
hypotheses and do not add generic status bits or new HA operating modes.

```sh
python3 energy_counters_v170.py /path/to/capture.pcap --output /tmp/energy.json
python3 -m unittest discover -s tests -p test_energy_counters.py
```

Full local results are saved in
`/home/bjwl/comfortzone-energy-analysis-20261114/week.json` and `panel.json`.
No new capture or pump register writes were needed.

## Next work

Keep the three daily electrical entities separate from these cumulative heat
counters. Investigate better mode allocation to reduce unassigned electricity,
and search unclassified register ranges for a genuine cumulative electrical
input counter. If none is found, ESPHome integration cannot reconstruct an
unobserved outage. Exposing clearer heat labels/derived heat totals is a
separate change requiring care with existing HA entity IDs and statistics.


## Allocation audit and correction, 2026-11-14

`allocation_audit_v170.py` reproduces the status/power association rules at
message timestamps. It splits integration at each expiry and reports the
reason why otherwise-known electrical input cannot be allocated. This is
an event-time left-hold approximation, not an exact simulation of the ESPHome
one-second right-integration schedule or historical HA statistics.

Replaying the complete week with the 45-second freshness bound:

| Rule | Total compressor electricity | Allocated heating + water | Allocated fraction |
| --- | --- | --- | --- |
| Previous pairing overwritten at every power reply | 101.422 kWh | 59.889 kWh | 59.05% |
| Preserve a previously confirmed, unchanged fresh status | 101.422 kWh | 95.969 kWh | 94.62% |
| Experimental 45-second initial pairing (not implemented) | 101.422 kWh | 96.319 kWh | 94.97% |

The old two-second pairing test accounted for 38.579 kWh of excluded input.
This explains a large total-versus-parts discrepancy without any excess power
measurement: known input continued into the total while both allocations
became unavailable. The raw capture can also miss packets in forwarding, so
these percentages are evidence from replay, not a guaranteed live loss rate.

The implemented correction preserves a confirmed association only while
status is unchanged and no older than 45 seconds. A new or changed status
still needs a power reply within 2 seconds. No new status interpretations,
heater assumptions or relaxed initial pairing were added.

After the correction, replay still leaves 5.453 kWh unallocated: 3.101 kWh
under the heater-active guard, 1.038 kWh lacking an initial close pair,
0.836 kWh under unmapped profiles and 0.478 kWh with expired status. These
amounts are not silently assigned to heating or hot water. The firmware
update cannot repair past daily-counter omissions.

```sh
python3 allocation_audit_v170.py /path/to/capture.pcap --output /tmp/allocation.json
python3 scan_energy_counters_v170.py /path/to/capture.pcap --sample-s 300 --output /tmp/candidates.json
```


### Sampling-method check

On 67,802 consecutive power intervals no longer than 45 s in the same week,
left integration gives 98.5006 kWh and right integration 98.4477 kWh, a 0.054%
difference. These intervals cover 593,781.52 s; 210 longer gaps are excluded
from both methods, so this is not the whole-week 101.422 kWh integral. This
comparison does not prove meter accuracy or rule out missing samples, but
shows that left-versus-right integration is far too small to explain the
reported total-versus-parts discrepancy. ESPHome currently uses one-second
right integration of its latest valid input-power state.


### Search for an independent electrical energy counter

The full week was scanned across 39 observed reply ranges in banks 0, 1, 3,
4 and 5. At every byte offset, complete unsigned 16/24/32/64-bit fields and
32/64-bit floating-point fields were interpreted in both endian orders.
Fields were not assembled across replies or mixed between endpoints.

The search examined 37,579 numeric interpretations (not 37,579 independent
registers). Range snapshots were sampled no more than once per 300 seconds.
5,761 interpretations had at least 12 increases and 12 well-covered half-hour
windows for comparison. Of these, 109 had no observed decreases and 305 had
at most eight. Very coarse counters, other encodings and unobserved registers
are not ruled out by this search.

No new credible cumulative compressor electricity counter emerged. The best
monotone input-correlated field is already-known `05:002c` compressor heat:
its fitted relative RMS increment error is 7.07% against input but 0.88%
against output. Byte-shifted/truncated/float interpretations of those same
bytes are aliases, not independent discoveries. Compressor-runtime fields
fit running hours much better than input; other near-monotone candidates
outside the known counter block fit elapsed time better than electrical input.
A fitted scale alone is insufficient evidence of energy semantics.

Full results: `/home/bjwl/comfortzone-energy-analysis-20261114/counter-search.json`.
The original 60-second-resolution attempt was stopped to bound processing
cost; the completed, reported scan uses 300 seconds. The scanner tests include
an unknown synthetic electrical counter that must be found and distinguished
from elapsed time, plus CRC/source separation and reset handling.

The practical next step is deploying the tested pairing-retention fix and
comparing **new increments over the same interval**. Existing daily deficits
will remain; waiting alone or renaming heat counters does not fill them.
