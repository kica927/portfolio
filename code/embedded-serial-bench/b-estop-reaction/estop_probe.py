"""E-STOP 반응지연 프로브 — 'G' 트리거마다 Uno 가 반응지연(µs)을 돌려준다."""
import argparse, statistics, struct, sys, time
try:
    import serial
except ImportError:
    sys.exit("pyserial 필요")
ap = argparse.ArgumentParser()
ap.add_argument("--port", required=True); ap.add_argument("--n", type=int, default=500)
a = ap.parse_args()
ser = serial.Serial(a.port, 115200, timeout=0.2); time.sleep(2.0); ser.reset_input_buffer()
vals, nofire = [], 0
for _ in range(a.n):
    ser.write(b"G"); r = ser.read(4)
    if len(r) != 4: nofire += 1; continue
    v = struct.unpack(">I", r)[0]
    if v == 0xFFFFFFFF: nofire += 1
    else: vals.append(v)
    time.sleep(0.002)
ser.close()
if not vals:
    print(f"no-fire {nofire}/{a.n} — D2↔D4 점퍼 확인 필요"); sys.exit()
vals.sort(); n = len(vals); mean = statistics.mean(vals)
jit = sum(abs(vals[i]-vals[i-1]) for i in range(1, n)) / max(1, n-1)
p = lambda q: vals[min(n-1, int(n*q))]
print(f"샘플 {n}/{a.n} · no-fire {nofire}")
print(f"반응지연 µs: mean {mean:.1f}  p50 {p(.5)}  p95 {p(.95)}  p99 {p(.99)}  max {vals[-1]}  min {vals[0]}")
print(f"지터(평균 |Δ|) {jit:.1f} µs · micros 분해능 4µs")
