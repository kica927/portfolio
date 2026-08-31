"""secure_framing 속성 기반 테스트 — 라운드트립·변조·위조·재전송."""
import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "protocol"))
import secure_framing as F
from hypothesis import given, strategies as st

KEY = b"grippers-preshared-key-2026"

payloads = st.fixed_dictionaries({
    "state": st.sampled_from(["IDLE","APPROACH","GRASP","CARRY","APPROACH_BOX","INSERT","DONE","ESTOP"]),
    "linear_x": st.floats(allow_nan=False, allow_infinity=False, width=32),
    "linear_y": st.floats(allow_nan=False, allow_infinity=False, width=32),
    "angular_z": st.floats(allow_nan=False, allow_infinity=False, width=32),
    "stop": st.booleans(),
})

@given(p=payloads, seq=st.integers(min_value=0, max_value=2**63))
def test_roundtrip(p, seq):
    d = F.decode(F.encode(p, seq, KEY), KEY)
    assert d.ok and d.reason is F.Reject.OK
    assert d.seq == seq and d.payload == p

@given(p=payloads, seq=st.integers(0, 2**32), i=st.integers(0, 10_000))
def test_bitflip_rejected(p, seq, i):
    frame = bytearray(F.encode(p, seq, KEY))
    j = i % len(frame)
    frame[j] ^= 0x01                       # 한 비트 뒤집기
    d = F.decode(bytes(frame), KEY)
    assert not d.ok                         # CRC 또는 HMAC 이 잡는다
    assert d.reason in (F.Reject.BAD_HMAC, F.Reject.BAD_CRC, F.Reject.BAD_LENGTH,
                        F.Reject.BAD_MAGIC, F.Reject.BAD_VERSION, F.Reject.BAD_JSON)

@given(p=payloads, seq=st.integers(0, 2**32))
def test_wrong_key_rejected(p, seq):
    # 키를 모르는 공격자는 유효 프레임을 못 만든다 (스푸핑 = F2 방어).
    d = F.decode(F.encode(p, seq, KEY), b"attacker-guessed-key")
    assert not d.ok and d.reason is F.Reject.BAD_HMAC

@given(st.integers(0, F.MIN_FRAME - 1))
def test_truncated_rejected(n):
    assert F.decode(b"\x00" * n, KEY).reason is F.Reject.TOO_SHORT

def test_replayguard_blocks_repeat():
    g = F.ReplayGuard(window=16)
    assert g.check(10) is True
    assert g.check(10) is False            # 같은 seq 재전송
    assert g.check(11) is True
    assert g.check(9) is True              # 창 안 재정렬은 허용
    assert g.check(9) is False             # 그러나 중복은 거부
    assert g.check(100) is True
    assert g.check(50) is False            # 창 밖 = 너무 오래됨
