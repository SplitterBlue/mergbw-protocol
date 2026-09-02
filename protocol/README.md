# MeRGBW / LT-06 Protocol Notes

Condensed reference. Full detail in the top-level `README.md`.

Device class: `Sunset lights` (LT-06, app device **type 5**, `夕阳灯`).
Service `fff0`, write `fff3`, notify `fff4`. Write without response.

## Frame format

```
Byte0:       0x55 (head)
Byte1:       cmd
Byte2:       seq — always 0xFF
Byte3:       length = 5 + payload_len (total frame length, incl. head and checksum)
Bytes4..n-2: payload
Byte n-1:    checksum = (~sum(previous bytes)) & 0xFF   (one's complement)
```

## Commands used by type 5

| Cmd | Name | Payload |
|-----|------|---------|
| `0x01` | POWER | `[1]` on, `[0]` off |
| `0x03` | SET_COLOR | `[R, G, B]` |
| `0x05` | SET_BRIGHTNESS | `[level]`, range 5–100 |
| `0x06` | SET_MODE | `[scene_index]`, a single byte for type 5 |

The full command table (`0x00`–`0x12`, `0xF1`–`0xF6`) is in the top-level README.
`0x10`/`0x11`/`0x12` (white light, white brightness, cold-and-warm) have no type-5 call
site; they belong to types 3, 6, 7 and 8.

## Brightness range and the wrap trap

`wire = slider + 5`, seekbar max 95, giving valid wire values of **5–100**.

Values above 100 wrap, non-monotonically:

| Wire | Output |
|------|--------|
| 5 | barely on |
| 50 | ~half |
| 100 | full (hardware ceiling) |
| 135 | dimmer than 100 |
| 255 | between 135 and 100 |

Clamp to 5–100. Mapping a 0–255 scale onto this byte makes "brighter" go dimmer.

## Amber

Type 5 has a physical amber emitter reached as a scene. `FF AA 5A` through `0x03` renders
as dim purple-white.

```
AMBER: 55 06 FF 06 86 19     scene 134 "Sunset"
```

- Brightness in scene mode uses the normal `0x05` command.
- Any `0x03` color frame exits the scene.
- Scenes 139 (`0x8B`, Sunrise) and 142 (`0x8E`, Summer sun) are untested.

## Frames

```
ON:    55 01 FF 06 01 A3
OFF:   55 01 FF 06 00 A4
RED:   55 03 FF 08 FF 00 00 A1
GREEN: 55 03 FF 08 00 FF 00 A1
BLUE:  55 03 FF 08 00 00 FF A1
DIM:   55 05 FF 06 05 9B
HALF:  55 05 FF 06 32 6E
FULL:  55 05 FF 06 64 3C
AMBER: 55 06 FF 06 86 19
```

## Status readback

Notify `fff4` can be enabled; the app logs incoming data as plain bytes with cmd in byte 1.
The type-5 status parser reports power and brightness. Scene and amber state are settable
and absent from the status format, so track them client-side.
