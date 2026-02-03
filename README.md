# MLP4840_CAN — BMS CAN Test Tool (SLCAN over COM, Windows)

This project is a Windows-based CAN test/validation script for a Battery Management System (BMS). It talks to a USB CAN adapter running **SLCAN (Lawicel-compatible)** firmware via a Windows **COM** port.

## Quick Summary

- Transport: Serial (COM port) to SLCAN adapter (e.g. USB CDC/UART)
- CAN: 11-bit IDs @ 500 kbps
- Query pattern: transmit `0x5A` (padded to DLC=8 by default)
- Reply format: 8 bytes total = 6-byte payload + CRC16
- CRC16: poly `0xA001`, init `0xFFFF` (Modbus-style), computed over bytes 0–5

## Files

- `test.py`: main test harness

## System Topology

```text
Windows PC
  │
  │  Serial / COM port (e.g. 115200 baud)
  │
USB↔CAN Adapter (SLCAN firmware)
  │
  │  CAN @ 500 kbps, 11-bit IDs
  │
BMS
```

Example TX intent:

- CAN ID: `0x100`
- Data (DLC=8): `5A 00 00 00 00 00 00 00`

Note:
- Some BMS accept DLC=1 (`5A`) only.
- Some require DLC=8 with padding.
- `test.py` currently defaults to DLC=8.

## Response Frame Format

- DLC: 8
- Layout:
  - Bytes 0–5: payload
  - Byte 6: CRC16 high byte
  - Byte 7: CRC16 low byte

## CRC16 Definition

- Polynomial: `0xA001`
- Initial value: `0xFFFF`
- Reflected / Modbus-style
- Calculated over bytes 0–5
- Transmitted as `[CRC_H][CRC_L]`

## Decoded CAN Messages

### CAN ID `0x100`

| Bytes | Field | Type | Scaling |
|---|---|---|---|
| 0–1 | Total Voltage | U16 | 10 mV |
| 2–3 | Current | S16 | 10 mA |
| 4–5 | Remaining Capacity | U16 | 10 mAh |
| 6–7 | CRC16 | — | — |

Conversions used by `test.py`:

- Voltage (V) = `raw * 0.01`
- Current (A) = `raw * 0.01`
- Capacity (Ah) = `raw * 0.01`

### CAN ID `0x101`

| Bytes | Field | Type | Scaling |
|---|---|---|---|
| 0–1 | Full Capacity | U16 | 10 mAh |
| 2–3 | Cycle Count | U16 | 1 |
| 4–5 | RSOC (%) | U16 | 1 |
| 6–7 | CRC16 | — | — |

## Requirements

### Hardware

- USB CAN adapter running SLCAN firmware
- Adapter appears as `COMx` in Windows
- Proper CAN termination (typically 120 Ω at each end of the bus)

### Software

- Python 3.9+
- `pyserial`

Install dependency:

```powershell
pip install pyserial
```

## Configuration

Edit the “USER CONFIG” block at the top of `test.py`:

- `PORT` (example: `COM6`)
- `BAUD` (example: `115200`)
- `CAN_SPEED_CMD` (example: `S6` for 500 kbps)
- `QUERY_IDS`
- `POLL_INTERVAL_S`

### Baud Rate vs CAN Bitrate

- `BAUD` is the serial speed between the PC and the SLCAN adapter.
- `CAN_SPEED_CMD` sets the CAN bitrate on the CAN side.

## SLCAN Init Sequence

The script uses this typical SLCAN command flow:

| Command | Meaning |
|---|---|
| `C` | Close CAN channel |
| `S6` | Set CAN speed to 500 kbps |
| `O` | Open CAN channel |
| `t` | Send standard (11-bit) CAN frame |

Example transmitted line (note the trailing `\r`):

```text
t10085A00000000000000\r
```

Meaning:

- `t` = standard frame
- `100` = CAN ID (hex)
- `8` = DLC
- `5A...` = data

## Run

From this folder:

```powershell
python test.py
```

## Expected Output (Example)

```text
RX ID=0x100 DATA=0FA003E800640123 CRC=OK (calc=0x0123 rx=0x0123)
   Decoded(0x100): V=40.00V  I=10.00A  RemCap=10.00Ah
```

## Troubleshooting

### `could not open port 'COM6': PermissionError(13, 'Access is denied.', None, 5)`

This is almost always Windows reporting that the COM port is already open in another application/process.

Fix:

- Close any other tool that might be using the port (PlatformIO Serial Monitor, Arduino Serial Monitor, PuTTY, another Python process).
- Confirm which port the adapter is on:

```powershell
python -m serial.tools.list_ports
```

- Unplug/replug the adapter if it’s stuck.

