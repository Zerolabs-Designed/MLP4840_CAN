# BMS CAN Test Tool (SLCAN over COM, Windows)

This project is a **Windows-based CAN test and validation tool** for a Battery Management System (BMS) using:

- **SLCAN (Lawicel-compatible) over COM port**
- **11-bit CAN identifiers**
- **500 kbps CAN bitrate**
- **CRC16 (polynomial `0xA001`, Modbus-style)**

The goal is to **replicate exactly what Cangaroo does**, but in a scriptable, repeatable way suitable for:
- protocol validation
- reverse engineering
- regression testing
- future automation or emulation

---

## System Overview

Windows PC
|
| COM Port (USB CDC / UART, e.g. 115200 baud)
|
USB-CAN Adapter (SLCAN firmware)
|
| CAN @ 500 kbps, 11-bit ID
|
BMS

ID : 0x100
DATA : 5A 00 00 00 00 00 00 00


> Some BMS accept only DLC=1 (`0x5A`), others require DLC=8 padded.
> This tool supports both.

---

### Response Frame Format
- DLC = 8
- Byte layout:

Byte 0–5 : Payload
Byte 6 : CRC16 High Byte
Byte 7 : CRC16 Low Byte


---

## CRC16 Definition

- Polynomial: `0xA001`
- Initial value: `0xFFFF`
- Algorithm: reflected / Modbus-style
- Calculated over **Byte 0–5**
- Transmitted as **[CRC_H][CRC_L]**

C reference implementation:
```c
uint16_t crc = 0xFFFF;
crc ^= byte;
crc = (crc >> 1) ^ 0xA001; // if LSB set

Decoded CAN Messages
CAN ID 0x100

| Bytes | Description              | Scaling |
| ----- | ------------------------ | ------- |
| 0–1   | Total Voltage (U16)      | 10 mV   |
| 2–3   | Current (S16)            | 10 mA   |
| 4–5   | Remaining Capacity (U16) | 10 mAh  |
| 6–7   | CRC16                    | —       |

Voltage = raw * 0.01 V
Current = raw * 0.01 A
Capacity = raw * 0.01 Ah

CAN ID 0x101

| Bytes | Description   | Scaling |
| ----- | ------------- | ------- |
| 0–1   | Full Capacity | 10 mAh  |
| 2–3   | Cycle Count   | 1       |
| 4–5   | RSOC (%)      | 1       |
| 6–7   | CRC16         | —       |


## Requirements
### Hardware

- USB-CAN adapter running SLCAN firmware
- Adapter appears as COMx in Windows
- Proper CAN termination (120 Ω)

### Software

- Python 3.9+
- pyserial

Install dependency:
~ pip install pyserial

### Configuration

Edit these values in the script:

~ PORT = "COM6"      # Must match the COM port used by Cangaroo
~ BAUD = 115200     # Fixed by adapter firmware

### Important Note on Baud Rate

This is NOT the CAN bitrate
This is the serial baud rate (PC ↔ adapter)

Cangaroo does not expose this
Common values:
115200 (most common)
230400 (some CANable clones)

If Cangaroo works, Python must use the same baud.



## SLCAN Initialization Sequence

The script uses the following standard SLCAN commands:

| Command | Meaning                        |
| ------- | ------------------------------ |
| `C`     | Close CAN channel              |
| `S6`    | Set CAN speed to 500 kbps      |
| `O`     | Open CAN channel               |
| `t`     | Send standard 11-bit CAN frame |

Example Transmitted Frame :
~ t10085A00000000000000\r

Meaning:

~ t      -> standard frame
~ 100    -> CAN ID (hex)
~ 8      -> DLC
~ 5A...  -> data

### Running the Tools

~ python slcan_bms_test.py

### Expected Output
~ RX ID=0x100 DATA=0FA003E800640123 CRC=OK
~ Decoded: V=40.00V  I=10.00A  RemCap=10.00Ah


