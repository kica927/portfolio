"""시리얼 링크 특성화 — RTT·처리량 vs payload(고정 baud) 또는 단일 baud 점."""
import argparse, statistics, sys, time
try:
    import serial
except ImportError:
    sys.exit("pyserial 필요")

def rtt_for(ser, size, n):
    payload = bytes((i & 0xFF) for i in range(size))
    frame = b"LT" + bytes([size]) + payload
    vals = []
    for _ in range(n):
        ser.reset_input_buffer(); t0 = time.perf_counter()
        ser.write(frame); r = ser.read(3 + size); t1 = time.perf_counter()
        if len(r) == 3 + size: vals.append((t1 - t0) * 1e3)
    return vals

def stats(vals):
    vals.sort(); n = len(vals)
    return statistics.mean(vals), vals[n//2], vals[min(n-1, int(n*.95))]

ap = argparse.ArgumentParser()
ap.add_argument("--port", required=True); ap.add_argument("--baud", type=int, default=115200)
ap.add_argument("--n", type=int, default=300); ap.add_argument("--payload-sweep", action="store_true")
ap.add_argument("--size", type=int, default=8)
a = ap.parse_args()
ser = serial.Serial(a.port, a.baud, timeout=0.3); time.sleep(2.0); ser.reset_input_buffer()
if a.payload_sweep:
    print(f"# baud={a.baud}  payload 스윕 (n={a.n})")
    print(f"{'bytes':>6} {'mean_ms':>8} {'p50':>7} {'p95':>7} {'thru_KBps':>10}")
    for size in [1, 4, 8, 16, 32, 64, 128, 200]:
        v = rtt_for(ser, size, a.n)
        if not v: print(f"{size:>6}  응답없음"); continue
        m, p50, p95 = stats(v)
        thru = (3 + size) / (m / 1e3) / 1024
        print(f"{size:>6} {m:>8.3f} {p50:>7.3f} {p95:>7.3f} {thru:>10.1f}")
else:
    v = rtt_for(ser, a.size, a.n)
    if v:
        m, p50, p95 = stats(v)
        print(f"baud={a.baud} size={a.size}: RTT mean {m:.3f} p50 {p50:.3f} p95 {p95:.3f} ms")
    else:
        print(f"baud={a.baud}: 응답없음")
ser.close()
