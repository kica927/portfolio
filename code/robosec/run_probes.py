"""모든 in-process probe 를 모아 돌린다. 하드웨어 불필요.

    PYTHONPATH=. python3 run_probes.py

grippers 도메인 계층을 읽기 전용으로 import 해, A1·A2·A4·A5·A6 방어가
코드상 성립하는지 지금 확정한다. 9월 8일 실기에서는 같은 공격을 실제
UDP 로 쏴서 '실기에서도 그런가'만 확증한다(RUNBOOK 참고).
"""

import importlib

PROBES = ["inprocess.probe_parse", "inprocess.probe_motion", "inprocess.probe_fsm"]


def main():
    all_results = []
    for name in PROBES:
        mod = importlib.import_module(name)
        print("=" * 64)
        all_results += mod.run()
        print()
    passed = sum(all_results)
    total = len(all_results)
    print("=" * 64)
    print(f"전체: {passed}/{total} 통과")
    if passed != total:
        print("\n실패 항목은 방어 부재(=발견)이거나 설계 변경 신호다. "
              "results/ 의 기록과 대조할 것.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
