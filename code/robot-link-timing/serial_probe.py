"""분산 로봇 링크 타이밍 프로브 — 시리얼 (Pi↔Arduino / 지금은 맥↔Arduino).

호스트가 프레임에 tx 시각을 걸고, Arduino echo 를 받아 왕복지연·지터·손실을 잰다.
(시리얼은 편도 분리가 어려워 왕복이 지표다.)

준비:  pip install pyserial   ·  Arduino 에 arduino/serial_echo 업로드(115200)
포트 찾기:  python serial_probe.py --list
사용:  python serial_probe.py --port /dev/cu.usbmodemXXXX --rate 200 --count 1000 --out serial.jsonl
"""
import argparse, json, struct, sys, time
try:
    import serial            # pyserial
    from serial.tools import list_ports
except ImportError:
    serial = None

MAGIC = b"LT"
HDR = struct.Struct(">2sI")      # magic, seq   (+payload +\n)


def now():
    return time.clock_gettime(time.CLOCK_MONOTONIC_RAW) if hasattr(time, "CLOCK_MONOTONIC_RAW") else time.perf_counter()


def do_list():
    for p in list_ports.comports():
        print(f"  {p.device}  {p.description}")


def probe(a):
    ser = serial.Serial(a.port, a.baud, timeout=0.2)
    time.sleep(2.0)                       # Arduino 리셋 대기
    ser.reset_input_buffer()
    pad = b"\x00" * max(0, a.size - HDR.size - 1)
    interval = 1.0 / a.rate if a.rate > 0 else 0.0
    tx = {}
    recs, loss = [], 0
    f = open(a.out, "w") if a.out else None
    for seq in range(a.count):
        frame = HDR.pack(MAGIC, seq) + pad + b"\n"
        tx[seq] = now()
        ser.write(frame)
        line = ser.read_until(b"\n")
        t_rx = now()
        if len(line) >= HDR.size and line[:2] == MAGIC:
            _, rseq = HDR.unpack(line[:HDR.size])
            if rseq in tx:
                rtt = (t_rx - tx.pop(rseq)) * 1e3
                rec = {"seq": rseq, "rtt_ms": rtt}
                recs.append(rec)
                if f: f.write(json.dumps(rec) + "\n")
        else:
            loss += 1
        if interval:
            dt = interval - (now() - tx.get(seq, now()))
            if dt > 0: time.sleep(dt)
    if f: f.close()
    ser.close()
    if not recs:
        print("응답 없음 — 포트/업로드/보드레이트 확인"); return
    r = sorted(x["rtt_ms"] for x in recs); n = len(r)
    mean = sum(r)/n
    jit = sum(abs(r[i]-r[i-1]) for i in range(1,n))/max(1,n-1)
    p = lambda q: r[min(n-1, int(n*q))]
    print(f"보낸 {a.count} · 받은 {n} · 미응답 {len(tx)+loss}")
    print(f"왕복 ms: mean {mean:.3f}  p50 {p(.5):.3f}  p95 {p(.95):.3f}  p99 {p(.99):.3f}  max {r[-1]:.3f}")
    print(f"지터(평균 |ΔRTT|) {jit:.3f} ms")
    if a.out: print(f"→ per-packet: {a.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--rate", type=float, default=200); ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--size", type=int, default=32); ap.add_argument("--out", default="")
    a = ap.parse_args()
    if serial is None:
        sys.exit("pyserial 필요: pip install pyserial")
    if a.list: return do_list()
    if not a.port: sys.exit("--port 필요 (먼저 --list)")
    probe(a)


if __name__ == "__main__":
    main()
