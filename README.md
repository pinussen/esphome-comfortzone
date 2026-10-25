# ComfortZone EX50 for ESPHome

ESP32/RS485 integration with asynchronous writes and protocol-170 decoding.
The protocol library originated with [qix67](https://github.com/qix67/comfortzone_heatpump);
this project builds the [pinussen fork](https://github.com/pinussen/comfortzone_heatpump).
The ESPHome integration originated with [vinnyspb](https://github.com/vinnyspb/esphome-comfortzone).

The current work is on **`feature/ex50-register-controls` in both repositories**.
Use the same branch for the package and external component. Loading a package
from one branch and its component from `main` can silently select older code.

[CODE-REVIEW.md](CODE-REVIEW.md) covers the code audit, EX50 manual/menu selection,
new entities and remaining uncertainties. [PROTOKOLL-170.md](PROTOKOLL-170.md)
documents the captured register evidence. [DIAGNOSTIK.md](DIAGNOSTIK.md) records
hardware diagnosis, deployment and live write tests.

[PROTOKOLL-PLAN.md](PROTOKOLL-PLAN.md) sets out the staged migration to a shared
register schema, generic decoding/writing and systematic capture analysis.

## What is supported

- Heating and hot-water climate entities, temperatures, powers and cumulative counters.
- Protocol 170 decodes fields by bank and byte address, including short and overlapping replies.
  Truncated fields and replies from another pump are not combined with old buffer contents.
- Actual compressor frequency uses panel-checked register `01:02e9`; the old
  `01:02d5` could retain a heating request during hot water production or a stop.
- Optional `comfortzone-protocol170.yaml`: ventilation Low/Normal/High, heating curve,
  start/stop extra-hot-water buttons, eleven additional sensors, pump clock and write result.
- A single asynchronous write at a time: up to 15 seconds waiting for a safe bus gap,
  then 200 ms for acknowledgement. Values are not confirmed merely because a request
  was queued. No automatic resend after a missing acknowledgement.
- Bounded UDP frame/raw-UART diagnostics and offline PCAP analysis.

The user confirmed that the change from 32 to 29.1 °C was made deliberately in
Home Assistant. The later 29.1 °C readbacks therefore confirm that HA control
worked; they are not evidence of the pump reverting the setting.
Protocol-170 mode/defrost/priority bits and split heating/hot-water CoP remain
unverified; their presence in a legacy YAML does not imply working readings.
The two split input-power sensors and their CoP therefore report unknown (`nan`)
until the required operating mode is known. Their daily energy totals cannot
provide a reliable split either. Repeated unknown derived values are suppressed;
finite power readings retain their updates for energy integration.

## Configuration

A complete HA Device Builder configuration is in
[comfortzone-ha.yaml.example](comfortzone-ha.yaml.example). Keep the existing
secrets used by the installed device. The example uses only published GitHub
packages and components, without a local library checkout.

Tested with ESPHome 2026.10.0, ESP-IDF 5.5.6 and ESP32 `wemos_d1_mini32`.
The repaired installation uses **TX26, RX16, DE+/RE21**. Pin selection must match
the actual wiring; its former GPIO17 was found stuck high.

```yaml
substitutions:
  tx_pin: "26"
  rx_pin: "16"
  re_de_pin: "21"
  comfortzone_protocol_version: "170"
  git_branch: "feature/ex50-register-controls"

packages:
  comfortzone_package: github://pinussen/esphome-comfortzone/comfortzone-package.yaml@feature/ex50-register-controls
  protocol170: github://pinussen/esphome-comfortzone/comfortzone-protocol170.yaml@feature/ex50-register-controls

esphome:
  name: comfortzone

esp32:
  board: wemos_d1_mini32
  framework:
    type: esp-idf

logger:
  level: INFO

api:
  encryption:
    key: !secret api_key
  custom_services: true

ota:
  - platform: esphome
    password: !secret ota_password

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

uart:
  id: uart_bus
  rx_full_threshold: 1
  rx_pin:
    number: ${rx_pin}
    mode:
      input: true
      pullup: true

comfortzone:
  detect_idle_break: true
```

`detect_idle_break` is installation-specific and defaults to false. It handles
this adapter's low RX line and spurious zero bytes between frames using physical
GPIO edge timing. It is not permission to transmit through arbitrary traffic.
`controller_address` defaults to `0x45726963` (“Eric”), the address used in the
successful GPIO26 tests.

For local development, `comfortzone-tx26-test.yaml` includes the recovery and
protocol-170 packages directly from this checkout and reads `secrets.yaml`.
`comfortzone-recovery.yaml` alone retains the earlier TX17 diagnostic setup.

```sh
esphome compile comfortzone-tx26-test.yaml
esphome upload comfortzone-tx26-test.yaml --device DEVICE_IP
esphome logs comfortzone-tx26-test.yaml --device DEVICE_IP
```

## Library and builds

The compiled C++ library is **vendored**, not fetched from the sibling checkout.
Its exact source commit and SHA256 hashes are in
`components/comfortzone/third_party/comfortzone_heatpump.lock.json`.
The library declares its own pinned FastCRC dependency so native ESP-IDF can
resolve `FastCRC.h`. ESPHome links the vendor directory directly to avoid stale
local library copies. `git_commit_hash` is not a library selector in this setup.

```sh
python3 scripts/sync_library.py --check
# After committing library changes in the sibling repository:
python3 scripts/sync_library.py --import-from ../comfortzone_heatpump
```

## Verification and protocol work

```sh
python3 tests/run_host_tests.py --fastcrc /path/to/FastCRC
python3 tests/run_host_tests.py --fastcrc /path/to/FastCRC --protocol 180
python3 -m unittest discover -s tests -p 'test_*.py'
python3 pcap_decode_v170.py capture.pcap --output decoded.json
```

The host runner supports protocols 160/170/180/221 and optional PCAP paths.
It compiles the real C++ decoder with a fake UART/clock under ASan/UBSan.
Tests and example configs contain no Wi-Fi/API credentials and do not contact a pump.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the two-repository workflow and captures.
