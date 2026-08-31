"""ros2 bag(.db3) -> invariant_check 가 읽는 JSONL. 맥에서 ROS2 없이 돈다.

pi_capture 의 record.sh 가 남긴 rosbag2 sqlite3 를 sqlite3+struct 로 직접
읽는다 — 맥에 ROS2 를 깔지 않아도 된다(humble 기본 저장소가 sqlite3).

뽑는 토픽:
    /mission/state   std_msgs/String       -> 현재 상태
    cmd_vel          geometry_msgs/Twist   -> 베이스로 나간 속도

출력 한 줄:
    {"t": 12.34, "state": "GRASP",
     "cmd": {"linear_x":..,"linear_y":..,"angular_z":..,"stop":false}}

state 는 최근값을 유지한다 — cmd_vel 레코드마다 그 시점의 최신 상태를 붙인다.
stop 은 Twist 에 없는 개념이라 항상 false 로 둔다(정지는 전 속도 0 으로 나타난다).

    python3 bag_to_jsonl.py <bag디렉터리 또는 .db3> -o out.jsonl
    python3 bag_to_jsonl.py --selftest
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import struct
import sys


def _decode_string(cdr: bytes) -> str:
    """std_msgs/String 의 CDR — 4B encapsulation + uint32 len + bytes."""
    if len(cdr) < 8:
        return ""
    little = cdr[1] == 1
    fmt = "<I" if little else ">I"
    n = struct.unpack_from(fmt, cdr, 4)[0]
    raw = cdr[8:8 + n]
    return raw.split(b"\x00", 1)[0].decode("utf-8", "replace")


def _decode_twist(cdr: bytes) -> tuple:
    """geometry_msgs/Twist — 4B encapsulation + 6×float64 (lin xyz, ang xyz)."""
    if len(cdr) < 4 + 48:
        return (0.0,) * 6
    little = cdr[1] == 1
    fmt = "<6d" if little else ">6d"
    return struct.unpack_from(fmt, cdr, 4)


def _open_db(path: str) -> str:
    if os.path.isdir(path):
        hits = glob.glob(os.path.join(path, "*.db3"))
        if not hits:
            raise SystemExit(f"'{path}' 안에 .db3 가 없습니다.")
        return sorted(hits)[0]
    return path


def convert(bag_path: str) -> list[dict]:
    db = _open_db(bag_path)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        topics = {name: tid for tid, name in
                  con.execute("SELECT id, name FROM topics")}
        state_id = topics.get("/mission/state")
        cmd_id = topics.get("cmd_vel")
        if cmd_id is None:
            raise SystemExit(f"cmd_vel 토픽이 bag 에 없습니다. 있는 토픽: {list(topics)}")

        rows = con.execute(
            "SELECT topic_id, timestamp, data FROM messages ORDER BY timestamp"
        ).fetchall()
    finally:
        con.close()

    t0 = rows[0][1] if rows else 0
    out = []
    current_state = "?"
    for topic_id, ts, data in rows:
        if topic_id == state_id:
            current_state = _decode_string(bytes(data))
        elif topic_id == cmd_id:
            lx, ly, _lz, _ax, _ay, az = _decode_twist(bytes(data))
            out.append({
                "t": round((ts - t0) / 1e9, 4),
                "state": current_state,
                "cmd": {"linear_x": lx, "linear_y": ly, "angular_z": az,
                        "stop": False},
            })
    return out


def _selftest() -> int:
    print("bag_to_jsonl 자가검증 — 직접 만든 CDR 블롭")
    ok = 0
    total = 0

    total += 1
    s = b"\x00\x01\x00\x00" + struct.pack("<I", 6) + b"GRASP\x00"
    got = _decode_string(s)
    good = got == "GRASP"
    ok += good
    print(f"  [{'PASS' if good else '**FAIL**'}] String 디코딩: {got!r}")

    total += 1
    tw = b"\x00\x01\x00\x00" + struct.pack("<6d", 0.1, -0.05, 0.0, 0.0, 0.0, 0.25)
    lx, ly, lz, ax, ay, az = _decode_twist(tw)
    good = abs(lx - 0.1) < 1e-9 and abs(ly + 0.05) < 1e-9 and abs(az - 0.25) < 1e-9
    ok += good
    print(f"  [{'PASS' if good else '**FAIL**'}] Twist 디코딩: lin=({lx},{ly}) ang_z={az}")

    total += 1
    big = b"\x00\x00\x00\x00" + struct.pack(">I", 4) + b"IDLE"
    good = _decode_string(big) == "IDLE"
    ok += good
    print(f"  [{'PASS' if good else '**FAIL**'}] 빅엔디안 String: {_decode_string(big)!r}")

    print(f"\n{ok}/{total} 통과")
    return 0 if ok == total else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ros2 bag -> invariant_check JSONL")
    ap.add_argument("bag", nargs="?", help="bag 디렉터리 또는 .db3 파일")
    ap.add_argument("-o", "--out", help="출력 JSONL (없으면 표준출력)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest or not args.bag:
        return _selftest()

    records = convert(args.bag)
    sink = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        for r in records:
            sink.write(json.dumps(r, ensure_ascii=False) + "\n")
    finally:
        if args.out:
            sink.close()
    print(f"{len(records)}개 레코드 -> {args.out or '표준출력'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
