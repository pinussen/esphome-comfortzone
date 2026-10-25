# Development

Clone `pinussen/esphome-comfortzone` and `pinussen/comfortzone_heatpump` beside
one another. Protocol changes belong in the library; ESPHome entity/platform
changes belong in this repository. Keep captured facts separate from hypotheses.

## Library workflow

1. Edit and test the library checkout.
2. Commit its sources.
3. Run `python3 scripts/sync_library.py --import-from ../comfortzone_heatpump`.
4. Run `python3 scripts/sync_library.py --check --source ../comfortzone_heatpump`.
5. Build/test ESPHome, then commit the component, vendor snapshot and lock together.

The sync script reads files from the specified checkout's **committed HEAD**.
Uncommitted sibling edits are deliberately not imported. Editing the vendor copy
without updating its snapshot is detected by `--check`.

Protocol-170 scalar read mappings live in the library's `registers_v170.json`.
After changing a mapping, run `python3 tools/generate_registers.py` there,
then test and commit the schema, generated header and reference together.
The vendored snapshot includes these files and the generator; Python tests
check that generated files match the schema. `pcap_decode_v170.py` reads the
vendored schema directly. Evidence levels distinguish inherited interpretations
from capture comparisons and panel observations. Ordinary read mappings do not
authorize writes; command encoding and write limits remain separate.

FastCRC revision: `c25258960e313a68237bf62db08770707955b82b` from
https://github.com/vinnyspb/FastCRC. Clone it outside this repo for host tests.

```sh
python3 tests/run_host_tests.py --fastcrc /path/to/FastCRC
python3 tests/run_host_tests.py --fastcrc /path/to/FastCRC --protocol 160
python3 tests/run_host_tests.py --fastcrc /path/to/FastCRC --protocol 180
python3 tests/run_host_tests.py --fastcrc /path/to/FastCRC --protocol 221
python3 -m unittest discover -s tests -p 'test_*.py'
esphome compile tests/configs/climate-only.yaml
esphome compile comfortzone-tx26-test.yaml
```

The first command accepts PCAP filenames after its options. Use `--library
../comfortzone_heatpump` to test the sibling sources with these same fixtures.
The protocol-170 tests exercise write validation/ACKs and bounded range decoding;
other-version tests sweep actual register-table addresses and packet lengths.
They cannot validate unknown register meanings or electrical signalling.

## Captures

The `debug_reroute` API action sends each processed frame once as a UDP payload
to `ip`, `port` for `timeout` seconds (1–3600). This is the ComfortZone protocol,
not Modbus. Capture at the destination before enabling the action. UDP is lossy;
only CRC-valid complete packets should inform register conclusions.

`debug_uart` additionally records UART bytes and GPIO samples, with sequence
numbers and dropped-record counts; its software timestamps are not a logic
analyser. The trace format and explicit intrusive diagnostics (`debug_direction`,
`debug_read_probe`, `debug_tx_pad`) are described in `DIAGNOSTIK.md`.
Never wire-test a TX pad while it is connected to the pump bus.

For a new menu mapping, record the menu value, change one setting on the panel,
and correlate W, acknowledgement and independent R readback. Revert that setting
and repeat. A read address from another firmware version, or a plausible number,
is not sufficient evidence to enable a write. Preserve anonymised minimal raw
fixtures and state precisely whether a test used a real pump or a fake bus.

`pcap_decode_v170.py` analyses overlapping blocks and history offline. Unknown
history codes and float-array sensor roles remain labelled candidates.
