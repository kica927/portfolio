"""pi_capture tap.py 의 토픽별 CSV -> invariant_check JSONL.

tap.py 는 토픽마다 CSV 를 하나씩 쓴다(구독만 하므로 미션에 영향 없음):
    cmd_vel.csv         컬럼: linear.x linear.y linear.z angular.x .. _wall _elapsed
    mission__state.csv  컬럼: data _wall _elapsed

이 둘을 _wall(벽시계) 순으로 병합해, cmd_vel 레코드마다 그 시점의 최신
상태를 붙인다 — invariant_check 가 읽는 {"t","state","cmd"} 스키마로.

record.sh(ros2 bag)를 썼다면 이 도구 대신 bag_to_jsonl.py 를 쓴다. 둘 중
어느 녹화 경로든 같은 JSONL 로 수렴한다.

    python3 csv_to_jsonl.py <tap.py 출력 디렉터리> -o run.jsonl
    python3 csv_to_jsonl.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys


def _find(dir_, *names):
    for n in names:
        p = os.path.join(dir_, n)
        if os.path.exists(p):
            return p
    hits = []
    for n in names:
        hits += glob.glob(os.path.join(dir_, f"*{n}*"))
    return hits[0] if hits else None


def _f(row, key):
    try:
        return float(row.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return float("nan")   # 수치가 아니면 nan — 그 자체가 검사기의 F 위반


def convert(cap_dir: str) -> list[dict]:
    cmd_csv = _find(cap_dir, "cmd_vel.csv", "cmd_vel")
    state_csv = _find(cap_dir, "mission__state.csv", "mission_state", "state.csv")
    if cmd_csv is None:
        raise SystemExit(f"cmd_vel CSV 를 못 찾음: {cap_dir}")

    # 상태 이벤트: (wall, state_str)
    states = []
    if state_csv:
        with open(state_csv, newline="") as f:
            for row in csv.DictReader(f):
                states.append((float(row["_wall"]), row.get("data", "?")))
    states.sort()

    def state_at(wall):
        cur = "?"
        for w, s in states:
            if w <= wall:
                cur = s
            else:
                break
        return cur

    out = []
    with open(cmd_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    t0 = float(rows[0]["_wall"]) if rows else 0.0
    for row in rows:
        wall = float(row["_wall"])
        out.append({
            "t": round(wall - t0, 4),
            "state": state_at(wall),
            "cmd": {
                "linear_x": _f(row, "linear.x"),
                "linear_y": _f(row, "linear.y"),
                "angular_z": _f(row, "angular.z"),
                "stop": False,
            },
        })
    return out


def _selftest() -> int:
    import tempfile
    print("csv_to_jsonl 자가검증 — 합성 CSV 두 개")
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "mission__state.csv"), "w", newline="") as f:
        f.write("_wall,_elapsed,data\n")
        f.write("100.0,0.0,IDLE\n")
        f.write("100.4,0.4,GRASP\n")
    with open(os.path.join(d, "cmd_vel.csv"), "w", newline="") as f:
        f.write("_wall,_elapsed,linear.x,linear.y,angular.z\n")
        f.write("100.1,0.1,0.1,0.0,0.0\n")     # IDLE 중 이동
        f.write("100.5,0.5,0.08,0.0,0.0\n")    # GRASP 중 이동 -> I1
    recs = convert(d)
    ok = 0
    total = 3
    ok += (len(recs) == 2)
    print(f"  [{'PASS' if len(recs)==2 else '**FAIL**'}] 레코드 2개: {len(recs)}")
    ok += (recs[0]["state"] == "IDLE")
    print(f"  [{'PASS' if recs[0]['state']=='IDLE' else '**FAIL**'}] 첫 cmd state=IDLE: {recs[0]['state']}")
    ok += (recs[1]["state"] == "GRASP")
    print(f"  [{'PASS' if recs[1]['state']=='GRASP' else '**FAIL**'}] 둘째 cmd state=GRASP: {recs[1]['state']}")
    print(f"\n{ok}/{total} 통과")
    return 0 if ok == total else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="pi_capture CSV -> invariant_check JSONL")
    ap.add_argument("capdir", nargs="?", help="tap.py 출력 디렉터리")
    ap.add_argument("-o", "--out", help="출력 JSONL")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest or not args.capdir:
        return _selftest()
    records = convert(args.capdir)
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
