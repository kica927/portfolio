"""RoboSec attacker 를 오라클로 — 실기 공격 페이로드를 보안 프레이밍에 건다.

robosec/protocol.py(공격자 관점 재구현)가 있으면 그걸 그대로 쓰고, 없으면
동일 규격을 인라인으로 만든다. 요지: 공격자는 '규격만' 알고 사전공유키는
모른다 — 그래서 A2 스푸핑이 막힌다.
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "protocol"))
import secure_framing as F

KEY = b"grippers-preshared-key-2026"

_ROBOSEC = pathlib.Path.home() / "Desktop/intel/robosec"
if (_ROBOSEC / "protocol.py").exists():
    sys.path.insert(0, str(_ROBOSEC))
    import protocol as P
    def valid_cmd_bytes():
        return P.command("APPROACH", linear_x=0.1)
    def corrupt_bytes():
        return P.raw({"state": "APPROACH", "linear_x": "not-a-number"})[:-3] + b"\xff\xff"
else:
    def valid_cmd_bytes():
        return json.dumps({"state":"APPROACH","linear_x":0.1,"linear_y":0.0,
                           "angular_z":0.0,"stop":False}).encode()
    def corrupt_bytes():
        return b'{"state":"APPROACH","linear_x":\xff\xff'

def test_A2_spoof_blocked_without_key():
    # 공격자는 유효 JSON 명령은 만들 수 있으나, 키가 없어 프레임을 서명 못 한다.
    payload = json.loads(valid_cmd_bytes())
    forged = F.encode(payload, seq=1, key=b"attacker-key")   # 틀린 키로 서명
    assert F.decode(forged, KEY).reason is F.Reject.BAD_HMAC
    # 프레이밍조차 안 하고 raw JSON 을 그대로 쏘면 최소 길이 미만이거나 HMAC 실패.
    assert F.decode(valid_cmd_bytes(), KEY).ok is False

def test_A1_corruption_blocked():
    d = F.decode(corrupt_bytes(), KEY)
    assert d.ok is False

def test_A3_replay_blocked():
    payload = json.loads(valid_cmd_bytes())
    g = F.ReplayGuard()
    frame = F.encode(payload, seq=42, key=KEY)
    d1 = F.decode(frame, KEY)
    assert d1.ok and g.check(d1.seq) is True     # 첫 수신 = 통과
    d2 = F.decode(frame, KEY)                     # 동일 프레임 재전송
    assert d2.ok and g.check(d2.seq) is False     # 서명은 유효하나 재전송으로 거부

def test_legit_sender_accepted():
    payload = json.loads(valid_cmd_bytes())
    d = F.decode(F.encode(payload, seq=7, key=KEY), KEY)
    assert d.ok and d.payload["state"] == "APPROACH"
