# F2 before/after — 보안 프레이밍이 스푸핑·재전송을 닫는다 (B2 W2)

> RoboSec · 2026-08-30 · 대상 파서: grippers `baseline_mission` `UdpHostLink._parse`(배포본)
> 방어: `udp-network-lab/secure_framing`(HMAC-SHA256 + CRC32 + ReplayGuard)

## 배경 — F2 란

실기(2026-08-30)에서 확증: Host→Pi 링크에 **송신자 인증·시퀀스가 없어**,
유효 상태(APPROACH)를 스푸핑하거나 낡은 명령을 재전송하면 미션 FSM 이 실제로
움직이고 바퀴 명령이 나간다. 상태 게이팅(D4)은 **불법 전이만** 막을 뿐,
합법으로 위장한 스푸핑은 못 막는다.

## 실험 — 동일 공격을 두 채널에

같은 타임라인(정상 명령 사이에 a2-spoof·a3-replay)을 두 수신 채널에 흘려 넣고,
각 채널이 통과시킨 명령열을 **진짜 `BaselineMission` FSM** 으로 돌려 비교했다.

| 채널 | 통과 | FSM base.velocity_calls | 공격 통과 |
|---|---|---|---|
| **OLD** 배포본 raw JSON | 4/4 (정상2 + 공격2) | 5회 | **2/2** |
| **NEW** 보안 프레이밍 | 2/4 (정상2만) | 3회 | **0/2** |

- NEW 거부 사유: **`BAD_HMAC`**(a2-spoof — 키 없는 공격자가 프레임 서명 불가),
  **`REPLAY`**(a3-replay — 유효 서명이어도 seq 가 이미 소비됨).
- **정상 명령은 양쪽 모두 통과** — 방어가 정상 트래픽을 깨지 않는다.
- 차이 velocity 2회(5→3) = 공격 패킷이 유발하던 바퀴 명령이 NEW 에서 사라짐.

## 결론

RoboSec 실기에서 F2 로 확증된 공격이, 링크에 HMAC(사전공유키)+시퀀스를
씌우자 **파서 이전 단계에서 전부 거부**된다. 상태 게이팅에 기대지 않고,
**인증되지 않은 명령이 FSM 에 닿기 전에** 막는다. 이것이 F2 의 진짜 방어이며,
CRC32 만으로는(공격자가 재계산 가능) 불가능했던 부분이다.

## 재현

```
cd ~/Desktop/intel/robosec
GRIPPERS_ROOT=~/Desktop/intel/grippers-baseline-wt PYTHONPATH=. \
  python3 f2_before_after.py
# 또는 run_tests.sh 5) 단계
```

## 다음 (W2 잔여 · W3)

- W2 잔여: Atheris 퍼즈로 `secure_framing.decode` 를 두들겨 파싱 견고성 확인.
- W3: 디코더 C 재구현 → libFuzzer/AFL++.
