"""보안 프레이밍을 씌운 수신 어댑터 (grippers-무관).

페이로드 해석은 주입받는다 — 이 저장소는 특정 애플리케이션을 import 하지 않는다.
decode(HMAC/CRC) → ReplayGuard(시퀀스) 를 통과한 것만 payload 로 넘긴다.
"""
from __future__ import annotations
from secure_framing import decode, ReplayGuard, Reject


class SecureLink:
    def __init__(self, key: bytes, parse_payload, window: int = 64):
        self.key = key
        self.guard = ReplayGuard(window)
        self.parse_payload = parse_payload
        self.rejects: list[Reject] = []

    def receive(self, frame: bytes):
        """프레임 하나를 받아 인증·재전송 검사 후 애플리케이션 명령을 돌려준다.
        거부되면 None (사유는 self.rejects 에 누적)."""
        d = decode(frame, self.key)
        if not d.ok:
            self.rejects.append(d.reason)
            return None
        if not self.guard.check(d.seq):
            self.rejects.append(Reject.REPLAY)
            return None
        return self.parse_payload(d.payload)
