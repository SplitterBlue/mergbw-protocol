# MeRGBW / LT-06 BLE Protocol

Extracted from the MeRGBW Android app (package `com.mergbw.android`) for LT-06 based lamps (e.g., "Sunset lights").

- Service: `0000fff0-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000fff3-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`

Frame format (unencrypted):
```
Byte0: 0x55 (head)
Byte1: cmd
Byte2: seq (0xFF for single commands)
Byte3: length = 5 + payload_len (includes head..checksum)
Bytes4..n-2: payload
Byte n-1: checksum = (~sum(previous bytes)) & 0xFF
```

Common commands:
- 0x01: power, payload `[1]` on / `[0]` off
- 0x03: RGB, payload `[R, G, B]`
- 0x05: brightness `[level]`
- 0x06: scene index `[idx]`
- 0x07: speed `[value]`
- 0x08: sensitivity `[value]`
- Others (alarms/time/DIY) use 0x0A/0x0B/0x0C/0x0E/0x0F/0x10/0x11/0x12 and sequence-based payloads.

Examples:
- ON: `55 01 FF 06 01 A3`
- OFF: `55 01 FF 06 00 A4`
- RED: `55 03 FF 08 FF 00 00 A1`
- GREEN: `55 03 FF 08 00 FF 00 A1`

See `protocol/README.md` for a concise copy of the notes.

## Python PoC

`poc.py` provides a minimal sender using Bleak:
```
pip install bleak
MERGBW_ADDRESS=FF:FF:11:38:3D:36 python poc.py on
python poc.py rgb 255 0 0
python poc.py brightness 128
```

Defaults:
- BLE MAC from `MERGBW_ADDRESS` env (falls back to `FF:FF:11:38:3D:36`)
- Writes to characteristic `0000fff3-0000-1000-8000-00805f9b34fb`
