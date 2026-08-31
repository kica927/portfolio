"""B2 W2 — F2 before/after: 같은 스푸핑·재전송 공격을 구파서 vs 보안프레이밍에.

RoboSec 실기(2026-08-30)에서 F2 로 확증된 것: 송신자 인증·시퀀스가 없어
유효 상태(APPROACH)를 스푸핑하거나 낡은 명령을 재전송하면 FSM 이 실제로
움직이고 바퀴 명령이 나간다. 이 스크립트는 동일 공격 타임라인을 두 채널에
흘려 넣고, 실제 BaselineMission FSM 이 무엇을 실행하는지 비교한다.

    OLD  = grippers 배포본 UdpHostLink._parse (raw JSON, 인증 없음)
    NEW  = secure_framing 어댑터 (HMAC + CRC + ReplayGuard)

두 채널의 결과 명령열을 각각 진짜 FSM 으로 돌려 base.velocity_calls 를 센다.
"""
import json
import pathlib
import sys
import threading

sys.path.insert(0, str(pathlib.Path.home() / "Desktop/포트폴리오/github/udp-network-lab/protocol"))
import harness  # noqa: F401  (GRIPPERS_ROOT → sys.path)
import secure_framing as SF
from secure_host_link import SecureLink

from domain.adapters.real.udp_host_link import UdpHostLink
from domain.adapters.fake.fake_arm import FakeArm
from domain.adapters.fake.fake_base import FakeBase
from domain.adapters.fake.fake_host_link import FakeHostLink, FakeLidar
from domain.adapters.fake.scripted_perception import ScriptedPerception
from domain.task.baseline_mission import BaselineMission, BaselinePorts, LinkWatchdog

KEY = b"grippers-preshared-key-2026"

# grippers 배포본 파서를 소켓 없이 쓴다(검증 로직만 재사용).
_deployed = object.__new__(UdpHostLink)
_deployed._logger = None
def deployed_parse_bytes(raw: bytes):
    return _deployed._parse(raw)
def deployed_parse_dict(d: dict):
    return _deployed._parse(json.dumps(d).encode("utf-8"))

# UdpHostLink._parse 가 부르는 _warn 을 무해화
UdpHostLink._warn = lambda self, *a, **k: None


def run_fsm(script):
    """명령열(HostCommand|None 리스트)을 진짜 FSM 으로 돌려 관측치를 돌려준다."""
    base = FakeBase()
    ports = BaselinePorts(
        base=base, arm=FakeArm(), perception=ScriptedPerception(),
        host=FakeHostLink(list(script)), lidar=FakeLidar(),
        estop=threading.Event(), watchdog=LinkWatchdog(),
    )
    gen = BaselineMission(ports).run()
    states = []
    for _ in range(len(script) + 2):
        try:
            states.append(next(gen).name)
        except StopIteration:
            break
    return states, base.velocity_calls


def main():
    # 공격 타임라인 — Pi 명령 포트에 도착하는 순서.
    legit1 = {"state": "APPROACH", "linear_x": 0.1, "linear_y": 0.0, "angular_z": 0.0, "stop": False}
    legit2 = {"state": "APPROACH", "linear_x": 0.1, "linear_y": 0.0, "angular_z": 0.0, "stop": False}
    spoof  = {"state": "APPROACH", "linear_x": 0.1, "linear_y": 0.0, "angular_z": 0.0, "stop": False}  # a2

    # --- OLD 채널: 배포본은 raw JSON 을 그대로 받는다 ---
    old_wire = [
        ("legit1", json.dumps(legit1).encode()),
        ("a2-spoof", json.dumps(spoof).encode()),
        ("a3-replay", json.dumps(legit1).encode()),  # 낡은 명령 재전송
        ("legit2", json.dumps(legit2).encode()),
    ]
    old_cmds, old_accepted = [], []
    for name, wire in old_wire:
        c = deployed_parse_bytes(wire)
        old_cmds.append(c)
        old_accepted.append(name if c is not None else None)

    # --- NEW 채널: 정상 송신자는 KEY 로 서명·증가 seq. 공격자는 KEY 없음 ---
    link = SecureLink(KEY, parse_payload=deployed_parse_dict)
    frame_legit1 = SF.encode(legit1, seq=1, key=KEY)
    new_wire = [
        ("legit1", frame_legit1),
        ("a2-spoof", json.dumps(spoof).encode()),          # 프레이밍 안 함(키 없음)
        ("a3-replay", frame_legit1),                       # 유효 프레임 재전송
        ("legit2", SF.encode(legit2, seq=2, key=KEY)),
    ]
    new_cmds, new_accepted = [], []
    for name, wire in new_wire:
        c = link.receive(wire)
        new_cmds.append(c)
        new_accepted.append(name if c is not None else None)

    # --- 두 명령열을 진짜 FSM 으로 ---
    old_states, old_vel = run_fsm(old_cmds)
    new_states, new_vel = run_fsm(new_cmds)

    def line(tag, accepted, states, vel):
        acc = [a for a in accepted if a]
        print(f"  [{tag}] 수신 4건 중 통과 {len(acc)}: {acc}")
        print(f"        FSM 상태={states}  base.velocity_calls={len(vel)}회")

    print("F2 before/after — 동일 스푸핑·재전송 공격을 두 채널에\n")
    print("공격: a2-spoof(APPROACH 0.1) · a3-replay(legit1 재전송), 사이사이 정상 명령\n")
    line("OLD  배포본 raw JSON", old_accepted, old_states, old_vel)
    line("NEW  보안 프레이밍  ", new_accepted, new_states, new_vel)
    print(f"\n  NEW 거부 사유: {[r.name for r in link.rejects]}")

    atk_old = sum(1 for a in old_accepted if a in ("a2-spoof", "a3-replay"))
    atk_new = sum(1 for a in new_accepted if a in ("a2-spoof", "a3-replay"))
    print(f"\n  공격 패킷 통과: OLD={atk_old}/2, NEW={atk_new}/2")
    ok = (atk_old == 2 and atk_new == 0
          and old_accepted.count("legit1") == 1 and new_accepted.count("legit1") == 1)
    print("  ✅ F2 닫힘 — 정상 명령은 양쪽 통과, 공격은 NEW 에서만 전부 차단"
          if ok else "  ⚠️ 기대와 다름")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
