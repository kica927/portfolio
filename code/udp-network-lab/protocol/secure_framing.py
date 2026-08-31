"""grippers Host↔Pi 링크에 씌우는 보안 프레이밍 계층 (RoboSec B2).

현 프로토콜(2026-08-26)은 UDP+UTF-8 JSON 다섯 필드에 **무결성·시퀀스·송신자
인증이 전부 없다.** RoboSec 실기(2026-08-30)에서 이 부재가 F2 로 확증됐다:
유효 상태(APPROACH)를 스푸핑하거나 낡은 명령을 재전송하면 FSM 이 실제로
전이하고 바퀴 명령이 나간다. CRC 만으로는 못 막는다 — 공격자가 CRC 를 다시
계산하기 때문이다. 스푸핑을 막는 것은 사전공유키 HMAC 이다.

이 모듈은 JSON 페이로드를 감싸는 프레임을 정의한다. 계층별로 다른 공격을 막는다:

    A1 손상 패킷  -> CRC32 무결성 (전송 오류·비트플립)
    A2 스푸핑     -> HMAC-SHA256(사전공유키) 인증  ← F2 의 진짜 방어
    A3 재전송     -> 단조 증가 시퀀스 + 수신 윈도우

와이어 포맷 (빅엔디안):

    +--------+-----+----------+--------+------------------+--------+-----------+
    | magic  | ver | seq(u64) | len(u16)| payload(len)    | crc32  | hmac(16)  |
    | 'GR'(2)| (1) |   (8)    |   (2)   |   JSON bytes     | (u32,4)| trunc(16) |
    +--------+-----+----------+--------+------------------+--------+-----------+

    - crc32 : magic..payload 전체 위에서 계산 (무결성).
    - hmac  : magic..crc32 전체 위에서 HMAC-SHA256, 앞 16바이트 (인증).
              hmac 은 항상 마지막 16바이트, crc 는 그 앞 4바이트라 len 필드를
              신뢰하지 않고도 버퍼 끝에서 위치를 잡는다 — MAC 검증 전에는
              어떤 헤더 필드도 신뢰하지 않는다.
"""
from __future__ import annotations

import hmac
import json
import struct
import zlib
from dataclasses import dataclass
from enum import Enum

MAGIC = b"GR"
VERSION = 1
_HEADER = struct.Struct(">2sB Q H")   # magic, ver, seq, len
_CRC = struct.Struct(">I")
_HMAC_LEN = 16
_HEADER_LEN = _HEADER.size            # 13
_TRAILER_LEN = _CRC.size + _HMAC_LEN  # 20
MIN_FRAME = _HEADER_LEN + _TRAILER_LEN


class Reject(Enum):
    OK = "ok"
    TOO_SHORT = "프레임이 최소 길이 미만"
    BAD_MAGIC = "매직 불일치"
    BAD_VERSION = "버전 불일치"
    BAD_LENGTH = "len 필드가 실제 페이로드와 불일치"
    BAD_CRC = "CRC32 불일치 (손상)"
    BAD_HMAC = "HMAC 불일치 (인증 실패·스푸핑)"
    REPLAY = "시퀀스가 창을 벗어남 (재전송·재정렬)"
    BAD_JSON = "페이로드 JSON 파싱 실패"


@dataclass(frozen=True)
class Decoded:
    ok: bool
    reason: Reject
    seq: int = 0
    payload: dict | None = None


def encode(payload: dict, seq: int, key: bytes) -> bytes:
    """JSON 페이로드를 seq 로 서명해 프레임 한 개를 만든다."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if seq < 0 or seq > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("seq 범위 초과")
    if len(body) > 0xFFFF:
        raise ValueError("페이로드가 65535바이트 초과")
    head = _HEADER.pack(MAGIC, VERSION, seq, len(body))
    integrity = head + body
    crc = _CRC.pack(zlib.crc32(integrity) & 0xFFFFFFFF)
    signed = integrity + crc
    tag = hmac.new(key, signed, "sha256").digest()[:_HMAC_LEN]
    return signed + tag


def decode(frame: bytes, key: bytes) -> Decoded:
    """프레임을 검사·복호한다. 검사 순서는 '인증 전에는 아무것도 신뢰 안 함'.

    반환은 항상 Decoded — 예외를 던지지 않는다(공격 입력에 대해 파싱 자체가
    실패 경로여야 하므로).
    """
    if len(frame) < MIN_FRAME:
        return Decoded(False, Reject.TOO_SHORT)

    # 1) HMAC 을 버퍼 끝(마지막 16바이트)에서 잡아 먼저 검증한다.
    signed, tag = frame[:-_HMAC_LEN], frame[-_HMAC_LEN:]
    expect = hmac.new(key, signed, "sha256").digest()[:_HMAC_LEN]
    if not hmac.compare_digest(tag, expect):
        return Decoded(False, Reject.BAD_HMAC)

    # 2) 인증됐으니 이제 헤더 필드를 신뢰한다.
    integrity, crc_raw = signed[:-_CRC.size], signed[-_CRC.size:]
    if zlib.crc32(integrity) & 0xFFFFFFFF != _CRC.unpack(crc_raw)[0]:
        return Decoded(False, Reject.BAD_CRC)

    magic, ver, seq, length = _HEADER.unpack(integrity[:_HEADER_LEN])
    if magic != MAGIC:
        return Decoded(False, Reject.BAD_MAGIC)
    if ver != VERSION:
        return Decoded(False, Reject.BAD_VERSION)
    body = integrity[_HEADER_LEN:]
    if length != len(body):
        return Decoded(False, Reject.BAD_LENGTH)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return Decoded(False, Reject.BAD_JSON)
    return Decoded(True, Reject.OK, seq=seq, payload=payload)


class ReplayGuard:
    """단조 증가 시퀀스 창. 이미 본 seq·너무 오래된 seq 를 재전송으로 거른다.

    간단한 슬라이딩 윈도우(최고 seq + 이미 본 최근 집합). UDP 는 재정렬될 수
    있으므로 '엄격히 최대'가 아니라 창 안의 새 seq 는 받아 준다.
    """

    def __init__(self, window: int = 64):
        self.window = window
        self.highest = -1
        self._seen: set[int] = set()

    def check(self, seq: int) -> bool:
        if seq > self.highest:
            self.highest = seq
            self._seen = {s for s in self._seen if s > seq - self.window}
            self._seen.add(seq)
            return True
        if seq <= self.highest - self.window:
            return False          # 너무 오래됨
        if seq in self._seen:
            return False          # 이미 본 것 (재전송)
        self._seen.add(seq)
        return True
