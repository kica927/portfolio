# udp-network-lab — 링크 계층 보안 하드닝

> 통신 프로토콜의 **무결성·인증·재전송 방어**를 재사용 가능한 프레이밍 계층으로.
> 출발점은 두 개의 실제 발견이다:
> - **2023 5G/UDP 인턴** — 오류주입 시험표에서 CRC32·시퀀스·발신자 ID 미검사 확인.
> - **2026 RoboSec(grippers)** — 그 부재가 로봇에서 **F2**로 확증됨: 유효 상태를
>   스푸핑하거나 낡은 명령을 재전송하면 FSM 이 실제로 전이하고 바퀴 명령이 나간다.
>
> 이 저장소는 그 결함을 닫는다.

## 문제 — CRC 는 스푸핑을 못 막는다

grippers 링크(2026-08-26 확정)는 UDP + UTF-8 JSON 다섯 필드이고 **무결성·시퀀스·
송신자 인증이 전부 없다.** 흔한 오해는 "CRC 를 붙이면 된다"이다. CRC 는 전송
오류(비트플립)를 잡지만 **공격자는 CRC 를 다시 계산**하므로 스푸핑을 못 막는다.
결함마다 맞는 계층이 다르다:

| 공격 (RoboSec) | 방어 계층 |
|---|---|
| A1 손상 패킷 | **CRC32** 무결성 |
| A2 스푸핑 (= F2) | **HMAC-SHA256(사전공유키)** 인증 |
| A3 재전송 | **단조 증가 시퀀스 + 수신 윈도우** |

## 와이어 포맷 (빅엔디안)

```
+--------+-----+----------+---------+---------------+--------+-----------+
| magic  | ver | seq(u64) | len(u16)| payload(len)  | crc32  | hmac(16)  |
| 'GR'(2)| (1) |   (8)    |   (2)   | JSON bytes    | (u32,4)| trunc(16) |
+--------+-----+----------+---------+---------------+--------+-----------+
```

- `crc32` = magic..payload 위에서 계산 (무결성).
- `hmac`  = magic..crc32 위에서 HMAC-SHA256, 앞 16바이트 (인증).
- **검사 순서 = 인증 전에는 아무것도 신뢰하지 않는다.** hmac 은 항상 마지막
  16바이트, crc 는 그 앞 4바이트라 `len` 필드를 신뢰하지 않고 버퍼 끝에서
  위치를 잡는다. HMAC 을 먼저 검증하고, 통과한 뒤에야 헤더 필드(seq/len)를 읽는다.

## 구현

- [`protocol/secure_framing.py`](protocol/secure_framing.py) — `encode` / `decode`
  (예외 없이 항상 `Decoded(ok, reason, seq, payload)` 반환) + `ReplayGuard`
  (재정렬 허용 슬라이딩 윈도우) + 거부 사유 `Reject` enum.

## 검증 (property-based + 실기 오라클)

`pytest` — 9개 통과:

- [`tests/test_framing.py`](tests/test_framing.py) — Hypothesis 로
  라운드트립 / 임의 비트플립 거부 / 틀린 키 거부 / 절단 거부 / ReplayGuard.
- [`tests/test_attacker_oracle.py`](tests/test_attacker_oracle.py) — **RoboSec
  attacker 를 오라클로** 물린다. `robosec/protocol.py` 가 있으면 그 공격
  페이로드를 그대로 쓴다:
  - **A2 스푸핑** — 키 없는 공격자가 유효 JSON 은 만들어도 프레임 서명은 못 함 → `BAD_HMAC`.
  - **A1 손상** — 손상 바이트 → 거부.
  - **A3 재전송** — 서명은 유효하나 같은 seq 재전송 → `ReplayGuard` 가 거부.
  - 정상 송신자 → 통과.

```
cd udp-network-lab && python3 -m venv .venv && .venv/bin/pip install pytest hypothesis
.venv/bin/python -m pytest -q
```

## 로드맵

- **W1 (완료)** — 와이어 포맷·코덱·property 테스트·attacker 오라클.
- **W2 (완료)** — Atheris 퍼즈(1,495만+402만 회, 크래시 0) + grippers 도메인에
  어댑터로 끼워 **F2 before/after** 확증(공격 OLD 2/2 통과 → NEW 0/2). → [`FUZZING.md`](FUZZING.md)
- **W3 (완료)** — 디코더 C 재구현 + **libFuzzer**(1,302만 회) + Python 레퍼런스와
  **차등 검증 7/7**. → [`FUZZING.md`](FUZZING.md) · [`native/`](native/)

## 범위 밖 (정직하게)

- 사전공유키의 **배포·회전**은 다루지 않는다(폐쇄 LAN 가정). 실전에선 키 관리가
  별도 과제다.
- HMAC 은 재전송 자체는 못 막는다(그래서 시퀀스가 별도 계층). 반대로 시퀀스는
  위조를 못 막는다(그래서 HMAC). 둘은 서로를 대체하지 않는다.
