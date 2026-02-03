import time
import serial

# ========= USER CONFIG =========
PORT = "COM6"          # <-- change to your COM port
BAUD = 115200          # common for SLCAN; try 230400 if needed
CAN_SPEED_CMD = "S6"   # S6 = 500kbps (Lawicel SLCAN standard)
QUERY_IDS = [0x100, 0x101]  # what you want to poll
POLL_INTERVAL_S = 0.2
# ===============================

CRC_16_POLY = 0xA001

def crc16_a001(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ CRC_16_POLY
            else:
                crc >>= 1
    return crc & 0xFFFF

def slcan_write(ser: serial.Serial, cmd: str):
    ser.write((cmd + "\r").encode("ascii"))
    ser.flush()
    time.sleep(0.02)

def slcan_open(ser: serial.Serial):
    # typical init sequence
    slcan_write(ser, "C")           # close if open
    slcan_write(ser, CAN_SPEED_CMD) # set bitrate
    slcan_write(ser, "O")           # open

def build_std_frame(can_id: int, data: bytes) -> str:
    # Standard 11-bit data frame: t + 3hex(ID) + 1hex(DLC) + data(hex)
    if can_id > 0x7FF:
        raise ValueError("Standard ID must be <= 0x7FF")
    if len(data) > 8:
        raise ValueError("DLC must be <= 8")
    return f"t{can_id:03X}{len(data):X}{data.hex().upper()}"

def send_query(ser: serial.Serial, can_id: int, dlc8: bool = True):
    # Your protocol says "use identifier + 0x5A as data".
    # Some BMS accept DLC=1 (only 0x5A), some want DLC=8 padded.
    if dlc8:
        payload = bytes([0x5A, 0, 0, 0, 0, 0, 0, 0])
    else:
        payload = bytes([0x5A])

    frame = build_std_frame(can_id, payload)
    slcan_write(ser, frame)

def parse_slcan_line(line: str):
    # We care about 't' standard frames.
    # Example: t10085A00000000000000
    if not line or line[0] != "t":
        return None
    if len(line) < 5:
        return None
    try:
        can_id = int(line[1:4], 16)
        dlc = int(line[4], 16)
        data_hex = line[5:5 + dlc * 2]
        if len(data_hex) != dlc * 2:
            return None
        data = bytes.fromhex(data_hex)
        return can_id, dlc, data
    except ValueError:
        return None

def decode_bms(can_id: int, data: bytes):
    # BMS replies: 8 bytes: byte0..5 payload, byte6..7 CRC16 (High, Low)
    if len(data) != 8:
        return

    payload = data[:6]
    crc_rx = (data[6] << 8) | data[7]
    crc_calc = crc16_a001(payload)
    ok = (crc_calc == crc_rx)

    print(f"RX ID=0x{can_id:03X} DATA={data.hex().upper()} CRC={'OK' if ok else 'BAD'} "
          f"(calc=0x{crc_calc:04X} rx=0x{crc_rx:04X})")

    if not ok:
        return

    # Based on your PDF:
    # 0x100: totalV (10mV, U16), current (10mA, S16), remCap (10mAh, U16)
    # 0x101: fullCap (10mAh, U16), cycles (U16), rsoc% (U16)
    if can_id == 0x100:
        v_raw = (payload[0] << 8) | payload[1]
        i_raw = ((payload[2] << 8) | payload[3])
        if i_raw & 0x8000:
            i_raw -= 0x10000
        c_raw = (payload[4] << 8) | payload[5]

        V = v_raw * 0.01   # 10mV -> 0.01 V
        I = i_raw * 0.01   # 10mA -> 0.01 A
        C = c_raw * 0.01   # 10mAh -> 0.01 Ah

        print(f"   Decoded(0x100): V={V:.2f}V  I={I:.2f}A  RemCap={C:.2f}Ah")

    elif can_id == 0x101:
        full_raw = (payload[0] << 8) | payload[1]
        cyc_raw  = (payload[2] << 8) | payload[3]
        rsoc_raw = (payload[4] << 8) | payload[5]

        print(f"   Decoded(0x101): FullCap={full_raw*0.01:.2f}Ah  Cycles={cyc_raw}  RSOC={rsoc_raw}%")

def main():
    with serial.Serial(PORT, BAUD, timeout=0.1) as ser:
        slcan_open(ser)
        print(f"SLCAN open on {PORT} @ {BAUD}. Polling {', '.join(hex(x) for x in QUERY_IDS)}")

        # Try DLC=8 first because your screenshot shows DLC=8 on both TX/RX
        dlc8 = True

        last_poll = 0.0
        while True:
            now = time.time()

            if now - last_poll >= POLL_INTERVAL_S:
                for cid in QUERY_IDS:
                    send_query(ser, cid, dlc8=dlc8)
                last_poll = now

            line = ser.readline().decode("ascii", errors="ignore").strip()
            if not line:
                continue

            parsed = parse_slcan_line(line)
            if not parsed:
                continue

            can_id, dlc, data = parsed
            if dlc == 8 and can_id in range(0x100, 0x14B):
                decode_bms(can_id, data)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
