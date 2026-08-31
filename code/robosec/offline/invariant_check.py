"""녹화 로그에서 안전 불변식 위반을 오프라인으로 찾는다.

9월 8일 실기에서 pi_capture 로 녹화한 상태·명령 스트림(JSONL)을 입력으로
받아, 크래시가 아니라 **불변식 위반**을 센다. 하드웨어 없이 지금은 합성
데이터로 검사기 자체를 검증한다(`--selftest`).

입력 JSONL 한 줄 스키마 (pi_capture 가 맞춰 녹화하면 된다):
    {"t": 12.34, "state": "GRASP",
     "cmd": {"linear_x": 0.0, "linear_y": 0.0, "angular_z": 0.0, "stop": false}}

검사하는 불변식 (security_properties.md 의 I1·I2·I5·I6):
    I1 파지 중 베이스 정지         state==GRASP 인데 cmd 속도가 0 이 아니면 위반
    I2 STOP 은 모든 속도를 0 으로   stop==true 인데 속도가 0 이 아니면 위반
    I5 속도 크기 물리 한계          |linear|>0.1(+여유) 또는 |angular|>0.25 면 위반
    I6 제자리회전 순수성            angular!=0 인데 linear!=0 이면 위반
"""

from __future__ import annotations

import argparse
import json
import math
import sys

LINEAR_CAP = 0.1
ROTATION_CAP = 0.25
MARGIN = 1.15   # 데드밴드·양자화 여유 15%
EPS = 1e-6


def _mag(cmd, *keys):
    return max(abs(float(cmd.get(k, 0.0))) for k in keys)


def check_record(rec) -> list[str]:
    """레코드 하나에서 발견한 위반 목록(불변식 ID + 설명)."""
    out = []
    state = rec.get("state", "?")
    cmd = rec.get("cmd", {})
    lx = float(cmd.get("linear_x", 0.0))
    ly = float(cmd.get("linear_y", 0.0))
    az = float(cmd.get("angular_z", 0.0))
    stop = bool(cmd.get("stop", False))
    lin = max(abs(lx), abs(ly))

    # 유한성 먼저 — nan/inf 는 그 자체로 위반(probe 로 찾은 결함의 로그 흔적)
    for nm, v in (("linear_x", lx), ("linear_y", ly), ("angular_z", az)):
        if not math.isfinite(v):
            out.append(f"F  비유한 속도 {nm}={v} (state={state})")

    if state == "GRASP" and (lin > EPS or abs(az) > EPS):
        out.append(f"I1 파지 중 베이스가 움직임 lin={lin:.3f} az={az:.3f}")
    if stop and (lin > EPS or abs(az) > EPS):
        out.append(f"I2 STOP 인데 속도 잔여 lin={lin:.3f} az={az:.3f}")
    if lin > LINEAR_CAP * MARGIN:
        out.append(f"I5 직진 크기 초과 {lin:.3f} > {LINEAR_CAP}")
    if abs(az) > ROTATION_CAP * MARGIN:
        out.append(f"I5 회전 크기 초과 {abs(az):.3f} > {ROTATION_CAP}")
    if abs(az) > EPS and lin > EPS:
        out.append(f"I6 회전에 병진 혼합 lin={lin:.3f} az={az:.3f}")
    return out


def scan(lines) -> dict:
    total = 0
    violations = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            violations.append((i, ["PARSE 레코드 파싱 실패"]))
            continue
        total += 1
        v = check_record(rec)
        if v:
            violations.append((i, v))
    return {"records": total, "violations": violations}


def _selftest() -> int:
    print("검사기 자가검증 — 합성 레코드")
    cases = [
        ({"state": "GRASP", "cmd": {"linear_x": 0, "angular_z": 0}}, 0, "파지 중 정지=정상"),
        ({"state": "GRASP", "cmd": {"linear_x": 0.05}}, 1, "파지 중 이동=I1"),
        ({"state": "APPROACH", "cmd": {"linear_x": 0.5}}, 1, "속도 초과=I5"),
        ({"state": "APPROACH", "cmd": {"linear_x": 0.1, "angular_z": 0.25}}, 1, "혼합=I6"),
        ({"state": "APPROACH", "cmd": {"stop": True, "linear_x": 0.5}}, 2, "STOP+과속=I2+I5"),
        ({"state": "APPROACH", "cmd": {"linear_x": float("nan")}}, 1, "nan=F"),
    ]
    ok = 0
    for rec, expect, note in cases:
        got = len(check_record(rec))
        good = got == expect
        ok += good
        print(f"  [{'PASS' if good else '**FAIL**'}] {note}: 위반 {got}개 (기대 {expect})")
    print(f"\n{ok}/{len(cases)} 통과")
    return 0 if ok == len(cases) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="오프라인 불변식 검사기")
    ap.add_argument("logfile", nargs="?", help="상태·명령 JSONL. 없으면 --selftest 권장")
    ap.add_argument("--selftest", action="store_true", help="합성 데이터로 검사기 검증")
    args = ap.parse_args(argv)

    if args.selftest or not args.logfile:
        return _selftest()

    with open(args.logfile, encoding="utf-8") as f:
        result = scan(f)
    print(f"레코드 {result['records']}개 · 위반 {len(result['violations'])}건")
    for idx, vs in result["violations"]:
        for v in vs:
            print(f"  line {idx}: {v}")
    return 1 if result["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
