"""RoboSec 공격 하네스 — 명령 소켓(5005)에 패킷을 주입한다.

⚠️ **주입은 하드웨어가 붙은 2026-09-08 이후에만 실기로 한다.** 그 전에는
`--target 127.0.0.1` 로컬 루프백에서 도구 자체의 동작만 검증한다. 기본은
`--dry-run` 이라 아무것도 보내지 않고 무엇을 보낼지 출력만 한다.

이 도구는 grippers 를 import 하지 않는다(공격자는 규격만 안다). 실기에서
겨누는 방어층은 Pi 쪽 코드다:
    A1 손상 패킷   -> D5 손상 패킷 폐기 (UdpHostLink._parse)
    A2 유효 명령   -> D1 속도 클램프  (motion.resolve_motion)
    A3 재전송      -> (시퀀스 번호 없음 — 방어 부재가 결과)
    A4 극단 수치   -> D1 속도 클램프
    A5 상태 불일치 -> D4 상태별 게이팅 (미션 FSM)
    A6 손실·중복·재정렬 -> D6 None != 정지 (워치독)

사용 예 (2026-09-08 이후, Pi IP 가 192.0.2.7 라 가정):
    python attacker.py list
    python attacker.py a1-corruption --target 192.0.2.7
    python attacker.py a4-extreme    --target 192.0.2.7 --state APPROACH
    python attacker.py a3-replay     --target 192.0.2.7 --count 20
"""

from __future__ import annotations

import argparse
import socket
import sys
import time

import protocol as P


class Injector:
    """UDP 명령 주입기. dry_run 이면 보내는 대신 기록만 한다."""

    def __init__(self, target_ip: str, port: int = P.COMMAND_PORT,
                 dry_run: bool = True):
        self.target = (target_ip, port)
        self.dry_run = dry_run
        self.sent: list[bytes] = []
        self._sock = None
        if not dry_run:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, payload: bytes, note: str = "") -> None:
        self.sent.append(payload)
        shown = payload[:120].decode("utf-8", "replace")
        tag = "DRY " if self.dry_run else "SEND"
        print(f"  [{tag}] {len(payload):>4}B  {note:<22} {shown}")
        if not self.dry_run:
            self._sock.sendto(payload, self.target)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()


# --- 공격들 -----------------------------------------------------------
# 각 함수는 Injector 를 받아 패킷을 흘려보낸다. 반환값은 보낸 개수.

def a1_corruption(inj: Injector, **_) -> int:
    """A1 — 손상 패킷. _parse 가 전부 버려야 한다(정지로도 취급하지 않음)."""
    cases = [
        (b"\xff\xfe\x00\x01not json", "비 UTF-8"),
        (b"{ this is not valid json", "깨진 JSON"),
        (b"{}", "빈 객체 (state 없음)"),
        (P.raw({"state": 123}), "state 가 수치"),
        (P.raw({"state": "APPROACH", "linear_x": "fast"}), "속도가 문자열"),
        (P.raw({"linear_x": 0.1}), "state 필드 누락"),
        (b"", "빈 페이로드"),
    ]
    for payload, note in cases:
        inj.send(payload, note)
    return len(cases)


def a2_spoof(inj: Injector, state: str = "APPROACH", **_) -> int:
    """A2 — 규격에 맞는 유효 명령 주입(스푸핑). 링크가 송신자를 안 보므로
    Pi 는 이것을 정상 Host 명령과 구분하지 못한다. 속도는 합의값이라
    클램프 자체는 안 걸린다 — 여기서 보는 것은 '받아들여지는가'다."""
    inj.send(P.command(state, linear_x=P.AGREED_LINEAR_MPS), "정상 크기 직진")
    inj.send(P.command(state, angular_z=P.AGREED_ROTATION_RAD_S), "정상 크기 회전")
    return 2


def a2_spin_impurity(inj: Injector, state: str = "APPROACH", **_) -> int:
    """A2 변형 — 제자리회전에 병진을 섞는다. D2 가 거부해야 한다."""
    inj.send(P.command(state, linear_x=0.1, angular_z=0.25), "회전+병진 혼합")
    return 1


def a4_extreme(inj: Injector, state: str = "APPROACH", **_) -> int:
    """A4 — 극단 수치. D1 이 크기만 잘라야 한다(방향 보존)."""
    cases = [
        (P.command(state, linear_x=1000.0), "직진 1000 m/s"),
        (P.command(state, linear_x=-1000.0), "후진 1000 m/s"),
        (P.command(state, angular_z=999.0), "회전 999 rad/s"),
        (P.command(state, linear_x=float("inf")), "직진 inf"),
        (P.command(state, linear_x=float("nan")), "직진 nan"),
    ]
    for payload, note in cases:
        inj.send(payload, note)
    return len(cases)


def a5_state_mismatch(inj: Injector, **_) -> int:
    """A5 — FSM 이 있는 곳과 다른 state. IDLE 에 GRASP 를 보내는 식."""
    cases = [
        (P.command("GRASP", linear_x=0.1), "IDLE 예상 위치에 GRASP"),
        (P.command("INSERT", linear_x=0.1), "순서 건너뛴 INSERT"),
        (P.command("BOGUS", linear_x=0.1), "규격 밖 state 문자열"),
    ]
    for payload, note in cases:
        inj.send(payload, note)
    return len(cases)


def a3_replay(inj: Injector, count: int = 10, state: str = "APPROACH", **_) -> int:
    """A3 — 같은 유효 명령을 반복 전송. 시퀀스 번호가 없어 중복을 못 거른다."""
    packet = P.command(state, linear_x=P.AGREED_LINEAR_MPS)
    for i in range(count):
        inj.send(packet, f"동일 패킷 {i + 1}/{count}")
        if not inj.dry_run:
            time.sleep(0.05)
    return count


ATTACKS = {
    "a1-corruption": a1_corruption,
    "a2-spoof": a2_spoof,
    "a2-spin-impurity": a2_spin_impurity,
    "a3-replay": a3_replay,
    "a4-extreme": a4_extreme,
    "a5-state-mismatch": a5_state_mismatch,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="RoboSec 공격 주입기")
    ap.add_argument("attack", choices=list(ATTACKS) + ["list"],
                    help="실행할 공격, 또는 목록 보기")
    ap.add_argument("--target", default=None,
                    help="Pi IP. 없으면 dry-run 강제 (아무것도 안 보냄)")
    ap.add_argument("--port", type=int, default=P.COMMAND_PORT)
    ap.add_argument("--state", default="APPROACH", help="주입할 state 필드")
    ap.add_argument("--count", type=int, default=10, help="replay 횟수")
    ap.add_argument("--live", action="store_true",
                    help="실제 전송. --target 과 함께여야 한다. 2026-09-08 이후 실기 전용")
    args = ap.parse_args(argv)

    if args.attack == "list":
        print("사용 가능한 공격:")
        for name, fn in ATTACKS.items():
            print(f"  {name:<18} {fn.__doc__.splitlines()[0]}")
        return 0

    dry = not (args.live and args.target)
    if args.live and not args.target:
        print("⚠️ --live 인데 --target 이 없다. dry-run 으로 내린다.", file=sys.stderr)
    where = args.target or "(dry-run, 전송 안 함)"
    print(f"공격: {args.attack}  대상: {where}:{args.port}  "
          f"모드: {'실전송' if not dry else 'DRY'}")

    inj = Injector(args.target or "127.0.0.1", args.port, dry_run=dry)
    try:
        n = ATTACKS[args.attack](inj, state=args.state, count=args.count)
    finally:
        inj.close()
    print(f"완료 — 패킷 {n}개 {'전송' if not dry else '준비(미전송)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
