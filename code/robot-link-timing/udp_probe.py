"""분산 로봇 링크 타이밍 프로브 — UDP (Host↔Pi).

NTP 식 4-타임스탬프 교환으로 왕복지연·편도지연·클럭오프셋·지터·손실·재정렬을 잰다.

    T0 prober tx → T1 responder rx → T2 responder tx → T3 prober rx
    RTT   = (T3-T0) - (T2-T1)            # 응답측 처리시간 제외
    offset= ((T1-T0) + (T2-T3)) / 2      # prober 대비 responder 클럭 오프셋
    oneway≈ RTT / 2  (경로 대칭 가정)

사용:
    (Pi/응답측)   python udp_probe.py responder --port 6000
    (맥/송신측)   python udp_probe.py prober --target <IP> --port 6000 \
                      --rate 100 --count 1000 --size 64 --out run.jsonl
루프백 검증: responder 를 127.0.0.1 로 띄우고 prober --target 127.0.0.1.
"""
import argparse, json, socket, struct, sys, time

MAGIC = b"LT"
# magic(2) seq(u32) t0(f64) t1(f64) t2(f64) size-pad
HDR = struct.Struct(">2sIddd")


def now() -> float:
    return time.clock_gettime(time.CLOCK_MONOTONIC_RAW) if hasattr(time, "CLOCK_MONOTONIC_RAW") else time.perf_counter()


def responder(args):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", args.port))
    print(f"responder on :{args.port} (Ctrl-C 종료)", file=sys.stderr)
    while True:
        data, addr = s.recvfrom(65535)
        t1 = now()
        if len(data) < HDR.size or data[:2] != MAGIC:
            continue
        magic, seq, t0, _, _ = HDR.unpack(data[:HDR.size])
        t2 = now()
        out = HDR.pack(MAGIC, seq, t0, t1, t2) + data[HDR.size:]
        s.sendto(out, addr)


def prober(args):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    pad = b"\x00" * max(0, args.size - HDR.size)
    interval = 1.0 / args.rate if args.rate > 0 else 0.0
    recs, last_seq, reorder, loss = [], -1, 0, 0
    f = open(args.out, "w") if args.out else None
    start = time.time()
    for seq in range(args.count):
        t0 = now()
        s.sendto(HDR.pack(MAGIC, seq, t0, 0.0, 0.0) + pad, (args.target, args.port))
        try:
            data, _ = s.recvfrom(65535)
            t3 = now()
        except socket.timeout:
            loss += 1
            continue
        _, rseq, r0, t1, t2 = HDR.unpack(data[:HDR.size])
        rtt = (t3 - r0) - (t2 - t1)
        offset = ((t1 - r0) + (t2 - t3)) / 2
        if rseq < last_seq:
            reorder += 1
        last_seq = max(last_seq, rseq)
        rec = {"seq": rseq, "rtt_ms": rtt * 1e3, "offset_ms": offset * 1e3,
               "oneway_ms": rtt * 1e3 / 2}
        recs.append(rec)
        if f:
            f.write(json.dumps(rec) + "\n")
        if interval:
            dt = interval - (now() - t0)
            if dt > 0:
                time.sleep(dt)
    if f:
        f.close()
    if not recs:
        print("응답 없음 (loss 100%)"); return
    rtts = sorted(r["rtt_ms"] for r in recs)
    n = len(rtts)
    mean = sum(rtts) / n
    jitter = sum(abs(rtts[i] - rtts[i-1]) for i in range(1, n)) / max(1, n-1)  # RFC3550 근사
    p = lambda q: rtts[min(n-1, int(n*q))]
    dur = time.time() - start
    print(f"보낸 {args.count} · 받은 {n} · 손실 {loss} ({100*loss/args.count:.1f}%) · 재정렬 {reorder}")
    print(f"RTT ms: mean {mean:.3f}  p50 {p(.5):.3f}  p95 {p(.95):.3f}  p99 {p(.99):.3f}  max {rtts[-1]:.3f}")
    print(f"지터(평균 |ΔRTT|) {jitter:.3f} ms · 편도 근사 {mean/2:.3f} ms · 클럭오프셋 중앙값 "
          f"{sorted(r['offset_ms'] for r in recs)[n//2]:.3f} ms · {n/dur:.0f} pkt/s")
    if args.out:
        print(f"→ per-packet: {args.out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("responder"); r.add_argument("--port", type=int, default=6000)
    p = sub.add_parser("prober")
    p.add_argument("--target", required=True); p.add_argument("--port", type=int, default=6000)
    p.add_argument("--rate", type=float, default=100); p.add_argument("--count", type=int, default=1000)
    p.add_argument("--size", type=int, default=64); p.add_argument("--out", default="")
    a = ap.parse_args()
    (responder if a.cmd == "responder" else prober)(a)


if __name__ == "__main__":
    main()
