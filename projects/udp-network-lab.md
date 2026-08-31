# udp-network-lab — 링크 계층 보안 하드닝

> *2026 · 단독 · 이력(보안) 연계 트랙*
>
> 통신 프로토콜의 **무결성·인증·재전송 방어**를 재사용 가능한 프레이밍 계층으로.
> 두 개의 실제 발견에서 출발한다 — 2023 통신 인턴의 정적 분석과, 2026 로봇의
> 실기 확증. 발견을 방어로 닫는 데까지 한 줄기로 잇는다.

---

## Problem — CRC 는 스푸핑을 못 막는다

- **2023 5G/UDP 인턴** — 오류주입 시험표에서 CRC32·시퀀스·발신자 ID 가 전부
  검사되지 않음을 확인했다. 당시엔 "동작한다"로 읽은 표가 지금은 위협 목록이다.
- **2026 RoboSec([grippers](grippers.md))** — 그 부재가 로봇에서 **F2** 로 확증됐다.
  유효 상태(APPROACH)를 스푸핑하거나 낡은 명령을 재전송하면 미션 FSM 이 실제로
  전이하고 바퀴 명령이 나간다.

흔한 오해는 "CRC 를 붙이면 된다" 이다. CRC 는 전송 오류(비트플립)를 잡지만
**공격자는 CRC 를 다시 계산**하므로 스푸핑을 못 막는다. 결함마다 맞는 계층이 다르다.

| 공격 | 맞는 방어 |
|---|---|
| A1 손상 패킷 | **CRC32** 무결성 |
| A2 스푸핑 (= F2) | **HMAC-SHA256(사전공유키)** 인증 |
| A3 재전송 | **단조 증가 시퀀스 + 수신 윈도우** |

## Architecture — 와이어 포맷

```
+--------+-----+----------+---------+---------------+--------+-----------+
| magic  | ver | seq(u64) | len(u16)| payload(len)  | crc32  | hmac(16)  |
| 'GR'(2)| (1) |   (8)    |   (2)   | JSON bytes    | (u32,4)| trunc(16) |
+--------+-----+----------+---------+---------------+--------+-----------+
```

- `crc32` = magic..payload, `hmac` = magic..crc 위에서 HMAC-SHA256 앞 16바이트.
- **검사 순서 = 인증 전에는 아무것도 신뢰하지 않는다.** hmac 은 항상 마지막
  16바이트라 `len` 필드를 신뢰하지 않고 버퍼 끝에서 위치를 잡는다. HMAC 을 먼저
  검증하고, 통과한 뒤에야 헤더(seq/len)를 읽는다.

## My Contribution

와이어 포맷·코덱·property 테스트·퍼즈 하네스·C 재구현을 직접 설계·구현하고,
RoboSec 에서 확증된 F2 공격을 이 방어로 닫는 것을 **실제 FSM 재생으로** 증명했다.

## Design Decisions

- **인증은 HMAC, 무결성은 CRC, 재전송은 시퀀스 — 서로를 대체하지 않는다.**
  HMAC 은 재전송을 못 막고(그래서 시퀀스), 시퀀스는 위조를 못 막는다(그래서 HMAC).
- **인증 우선 순서.** 인증되지 않은 입력은 파서에 닿기 전에 잘린다 → 공격면 축소.
- **정직한 비평: CRC32 는 HMAC 뒤에서 사실상 잉여다.** HMAC 이 CRC 까지 덮으므로
  인증 통과 프레임은 CRC 도 항상 맞다. 규격 완결성·계층 분리 목적으로 남기되
  보안 실효는 HMAC 이 전담한다. 이 중복을 아는 채로 두는 것과 모르고 두는 것은
  다르다.

## Implementation

- `protocol/secure_framing.py` — `encode`/`decode`(예외 없이 항상 `Decoded` 반환) +
  `ReplayGuard`(재정렬 허용 슬라이딩 윈도우) + `Reject` 사유 enum.
- `protocol/secure_host_link.py` — 페이로드 해석을 주입받는 grippers-무관 수신 어댑터.
- `native/secure_framing.c` — 같은 포맷의 C 재구현. CRC32 직접 구현, HMAC-SHA256 은 OpenSSL.

## Verification

| 구분 | 도구 | 결과 |
|---|---|---|
| 단위·속성 | pytest + Hypothesis | **9/9** — 라운드트립·비트플립·위조키·절단·ReplayGuard·attacker 오라클 |
| **F2 실증** | 실제 `BaselineMission` FSM 재생 | 공격 통과 **OLD 2/2 → NEW 0/2** (BAD_HMAC·REPLAY), 정상 명령은 양쪽 통과 |
| 퍼징(Python) | Atheris ×2 | **1,495만 + 402만 회 / 크래시 0** |
| 퍼징(C) | libFuzzer + ASan | **1,302만 회 / 크래시 0** |
| 퍼징(C·2번째 도구) | AFL++ (persistent, ASan) | **735만 회 / 122k exec·s⁻¹ / 크래시·행 0** (2026-08-31, 맥) |
| 교차 검증 | C vs Python 레퍼런스 | **7/7 차등 일치** |

**F2 before/after 가 핵심 산출물이다** — RoboSec 실기에서 확증된 그 공격이,
링크에 HMAC+시퀀스를 씌우자 FSM 에 닿기 전에 전부 거부됐다.

## Results

- 발견(2023 정적 · 2026 실기) → 방어(2026) 로 **한 서사가 닫혔다.**
- 로드맵이 *"libFuzzer/AFL++ 는 실제로 쓴 뒤에 올린다"* 고 못 박았던 부분을,
  Atheris·libFuzzer 실행 기록으로 채웠다.
- Python 레퍼런스와 C 구현이 같은 규격임을 차등 검증으로 기계적으로 보였다.

## Limitations

- 사전공유키의 **배포·회전**은 범위 밖이다(폐쇄 LAN 가정). 실전에선 키 관리가 별도 과제다.
- CRC32 는 HMAC 뒤에서 잉여다(위 설계 비평). 계층 분리를 위해 남겼다.
- 퍼저의 낮은 커버리지(raw 입력)는 곧 공격면이 좁다는 뜻이지만, 인증 뒤 파서
  견고성은 별도 하네스로만 확인했다 — 실제 grippers 프로덕션 통합은 아직 안 했다.

## Future Work

- grippers 에 실제 수신 어댑터로 통합(Ports & Adapters 라 교체가 국소적이다).
- ~~C 디코더를 AFL++ 로도~~ **완료** — AFL++ persistent 로 735만 회(크래시 0, bitmap 39%). 두 퍼저 모두 무결점.
- 키 회전·재생성 절차 설계.

---

**코드**: [`code/udp-network-lab/`](../code/udp-network-lab/) · **관련**: [RoboSec](robosec.md) · [grippers](grippers.md) · [5G/UDP 프로토타입](5g-udp-prototype.md)
