# MeRGBW / LT-06 Protocol Notes

Device: `Sunset lights` (`FF:FF:11:38:3D:36`), service `fff0`, write `fff3`, notify `fff4`.

Frame format (unencrypted):
```
Byte0: 0x55 (head)
Byte1: cmd
Byte2: seq (0xFF for single commands)
Byte3: length = 5 + payload_len (includes head..checksum)
Bytes4..n-2: payload
Byte n-1: checksum = (~sum(previous bytes)) & 0xFF
```

Common commands seen in APK (`com.mergbw.android`):
- 0x01: power, payload `[1]` on / `[0]` off
- 0x03: RGB, payload `[R,G,B]`
- 0x05: brightness `[level]`
- 0x06: scene index `[idx]`
- 0x07: speed `[value]`
- 0x08: sensitivity `[value]`
- Other app features use 0x0A/0x0B/0x0C/0x0E/0x0F/0x10/0x11/0x12 for alarms/time/DIY, plus `getSeqCommand` for larger payloads.

Examples (tested):
- ON: `55 01 FF 06 01 A3`
- OFF: `55 01 FF 06 00 A4`
- RED: `55 03 FF 08 FF 00 00 A1`
- GREEN: `55 03 FF 08 00 FF 00 A1`

Notify `fff4` can be enabled; app logs incoming data as plain bytes with cmd in byte1.
