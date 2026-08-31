"""embedded-serial-security — 호스트 프로브.
Uno 의 프레이밍 디코더를 상대로: 정상·손상(CRC)·재전송(seq)·퍼징(임의 바이트)."""
import argparse, random, struct, sys, time, zlib
try:
    import serial
except ImportError:
    sys.exit("pyserial 필요: pip install pyserial")

M = b"SF"
STATUS = {0: "OK", 2: "BAD_LEN", 3: "BAD_CRC", 4: "REPLAY", 5: "TRUNCATED"}

def frame(seq: int, payload: bytes) -> bytes:
    integ = M + struct.pack(">IB", seq, len(payload)) + payload
    return integ + struct.pack(">I", zlib.crc32(integ) & 0xFFFFFFFF)

def txn(ser, raw: bytes):
    ser.reset_input_buffer(); ser.write(raw)
    r = ser.read(7)
    if len(r) == 7 and r[:2] == M:
        return STATUS.get(r[2], f"0x{r[2]:02x}"), struct.unpack(">I", r[3:7])[0]
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True); ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args()
    ser = serial.Serial(a.port, a.baud, timeout=0.3); time.sleep(2.0); ser.reset_input_buffer()
    seq = 1
    print("== 정상 프레임 3개 (기대 OK) ==")
    for _ in range(3):
        s, rs = txn(ser, frame(seq, b"APPROACH")); print(f"  seq={seq} → {s}"); seq += 1
    print("== 손상: 페이로드 1바이트 뒤집기 (기대 BAD_CRC) ==")
    good = bytearray(frame(seq, b"APPROACH")); good[8] ^= 0x01
    s, _ = txn(ser, bytes(good)); print(f"  seq={seq} → {s}"); seq += 1
    print("== 재전송: 낡은 seq=2 다시 (기대 REPLAY) ==")
    s, _ = txn(ser, frame(2, b"APPROACH")); print(f"  seq=2 → {s}")
    N = 800
    print(f"== 퍼징: 임의 바이트 {N}회 (보드가 hang/오수용 하나?) ==")
    rng = random.Random(1); spurious_ok = 0; responded = 0
    ser.timeout = 0.02                       # 퍼징은 무응답이 정상 → 짧게
    for _ in range(N):
        blob = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 48)))
        s, _ = txn(ser, blob)
        if s is not None: responded += 1
        if s == "OK": spurious_ok += 1
    ser.timeout = 0.3
    print(f"  응답한 임의입력 {responded}/{N} · 잘못 OK 수용 {spurious_ok}")
    print("== 퍼징 후 생존 확인: 정상 프레임 (기대 OK) ==")
    s, _ = txn(ser, frame(seq, b"ALIVE")); print(f"  seq={seq} → {s}")
    ser.close()

if __name__ == "__main__":
    main()
