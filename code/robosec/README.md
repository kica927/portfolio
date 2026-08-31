> **공개 스냅샷 안내.** 실제 네트워크 IP 는 문서용 placeholder(`192.0.2.x`, RFC5737 TEST-NET)로 치환했고, 스크립트는 `PI_IP`·`PI` 등 env 변수로 실제 값을 받습니다. 대상 로봇 코드는 공개 저장소 [`grippers-intel/grippers`](https://github.com/grippers-intel/grippers)(개인 미러 `kica927/grippers`)입니다. 이 툴킷은 **자신이 만든 로봇을 대상으로** 하는 방어적 보안 테스트용입니다.

# RoboSec — grippers 링크 보안 테스트 하네스

grippers 의 Host↔Pi UDP 링크(5005/5006)를 대상으로, **크래시가 아니라 안전
불변식 위반**을 찾는 도구 모음이다. 방법론·위협 모델·불변식 정의는 포트폴리오
저장소의 문서에 있고, 여기에는 **실행되는 코드와 실측 결과**가 있다.

- 방법론/위협모델/불변식:
  [`portfolio/plans/robosec/`](https://github.com/kica927/portfolio/tree/main/plans/robosec)
- 하드웨어 마지막 날 계획:
  [`portfolio/plans/2026-09-08-capture.md`](https://github.com/kica927/portfolio/blob/main/plans/2026-09-08-capture.md)

## 핵심 설계 — 하드웨어 없이 대부분을 확정한다

grippers 는 Ports & Adapters 라, 도메인 계층이 하드웨어·ROS 없이 Fake 어댑터로
끝까지 돈다. 그래서 **공격의 대부분을 지금 in-process 로 확정**하고, 9월 8일
실기에서는 "실물에서도 같은가"만 확증한다.

    A1 손상 패킷   -> D5 폐기            → probe_parse  (로컬 UDP 로 실제 링크 검증)
    A2 유효 명령   -> (인증 없음)         → probe_fsm
    A2 회전+병진   -> D2 거부            → probe_motion
    A4 극단 수치   -> D1 클램프          → probe_motion
    A5 상태 불일치 -> D4 게이팅          → probe_fsm
    A6 손실(None)  -> D6 (None!=정지)    → probe_fsm

## 구성

| 경로 | 무엇 |
|---|---|
| `protocol.py` | 링크 프로토콜의 **독립 재구현** — 공격자는 규격만 안다(grippers import 안 함) |
| `attacker.py` | UDP 주입 CLI. 기본 dry-run, `--live`+`--target` 이라야 실전송 (9월 8일 전용) |
| `harness/` | grippers 도메인 계층을 읽기 전용으로 import (PYTHONPATH 만 얹음) |
| `inprocess/probe_parse.py` | A1 — 실제 `UdpHostLink` 를 로컬 루프백에 띄워 손상 패킷 검증 |
| `inprocess/probe_motion.py` | A2·A4 — `resolve_motion` 순수함수로 클램프·회전순수성 검증 |
| `inprocess/probe_fsm.py` | A5·A6 — 실제 `BaselineMission` 을 Fake 로 구동, 게이팅 검증 |
| `run_probes.py` | 세 probe 를 모아 실행 |
| `offline/bag_to_jsonl.py` | **pi_capture** `record.sh` 의 ros2 bag(.db3) → JSONL. 맥에서 ROS2 없이 |
| `offline/csv_to_jsonl.py` | **pi_capture** `tap.py` 의 토픽별 CSV → JSONL |
| `offline/invariant_check.py` | 녹화 JSONL 에서 I1·I2·I5·I6 위반 스캔 (9월 8일 이후) |
| `results/` | 실측 결과 기록 |
| `RUNBOOK_2026-09-08.md` | 실기 당일 실행 순서 |

## pi_capture 와의 관계 — 녹화는 pi_capture, 주입·분석은 RoboSec

RoboSec 에는 **녹화 기능이 없다.** 녹화는 `~/Desktop/intel/pi_capture` 가 한다
(구독만 하는 안전 설계). 두 도구는 겹치지 않고 이어진다.

```
pi_capture (Pi)              RoboSec (맥)
  tap.py / record.sh   ──►   attacker.py   명령 주입 (9월 8일 실기)
     녹화(구독만)              (동시에)
       │                         │
       ▼                         ▼
   CSV 또는 bag  ──────────►  csv_to_jsonl / bag_to_jsonl  ──►  invariant_check
                                                                   위반 탐지
```

pi_capture 는 의도적으로 **명령을 주입하지 않는다**(그 README §4). 능동적인
공격은 RoboSec 의 `attacker.py` 가 담당한다. 그래서 RoboSec 실험은 grippers
정상 미션과 **분리된 전용 세션**에서, pi_capture 녹화를 켜 둔 채로 한다.

## 실행

    cd ~/Desktop/intel/robosec
    PYTHONPATH=. python3 run_probes.py               # in-process 전체 (현재 20/21)
    python3 offline/invariant_check.py --selftest    # 오프라인 검사기 자가검증
    python3 attacker.py list                          # 공격 목록

grippers 저장소가 다른 경로면 `GRIPPERS_ROOT=/경로` 를 앞에 붙인다.
Python 3.11 로 돌리려면 `~/Desktop/intel/.venv_test/bin/python` 을 쓴다
(Pi 런타임과 같은 버전 — 교차검증용).

## 현재 결과 (2026-08-30, 하드웨어 이전)

**20/21.** 유일한 미통과가 실제 발견이다.

- **F1 🔴 NaN 속도가 D5·D1 두 방어를 모두 통과**해 `apply_velocity(nan,…)` 까지
  도달한다. `min(abs(nan), limit)` 이 nan 이라 클램프가 무력하다.
- **F2 🟡 상태 게이팅은 전이만 막고 속도는 막지 않는다** — 인증 없는 소켓과
  합치면 IDLE 로봇을 임의 속도로 움직일 수 있다.

자세한 근거·제안·확증 계획은 [`results/inprocess_2026-08-30.md`](results/inprocess_2026-08-30.md).

## 원칙

- **grippers 저장소를 수정하지 않는다.** import 만 한다. F1 방어 추가는 grippers
  팀의 판단이며, 이 하네스는 결함을 **보이는** 데까지가 역할이다.
- **실전송은 9월 8일 이후 실기에서만.** 그 전 모든 것은 dry-run 또는 로컬 루프백.
- 하드웨어 접근은 2026-09-08 종료. 이후 in-process·오프라인 부분은 계속 유효하다.
