# 로드맵 — 보안 연구로 가는 길

> 전체 계획의 요약입니다. 이 저장소가 **지금 어디쯤이고 다음이 무엇인지** 알기
> 위한 지도이며, 프로젝트가 실체를 갖추면 그때 별도 저장소로 분리합니다.

---

## 한 문장

> **공부 자체를 포트폴리오로 만들지 않고, 공부 → 실습 → 분석 → 실제 시스템 적용 →
> 실험 결과라는 연속된 증거를 만든다.**

## 기술 축

```
Math / Electronics / 5G
          ↓
C → CS:APP → OSTEP → Security → Binary Analysis → Fuzzing
                                                     ↓
                                                  RoboSec
```

기존 경험(수학 → 전자공학 → 5G/UDP 통신 → ROS 2 / Physical AI)을
**Software / Systems / Cyber-Physical Security** 로 잇는 것이 목표입니다.

---

## 현재 위치

| | 프로젝트 | 상태 |
|---|---|---|
| ✅ | [grippers](../projects/grippers.md) | 완료 — 실기 검증까지 |
| ✅ | [grippers-host-mac](../projects/grippers-host-mac.md) | 완료 |
| ✅ | [5G/UDP 프로토타입](../projects/5g-udp-prototype.md) | 2023 (코드 비공개) |
| ✅ | [Pell 방정식 연구](../projects/pell-equations.md) | 2022 |
| 🟡 | [robosec](robosec/README.md) | 설계 단계 — 위협 모델·불변식 작성 완료 |
| 📅 | systems-security-lab | 2026-10 착수 |
| 📅 | udp-network-lab | 2026-12 착수 |
| 📅 | cryptography-lab | 보조 트랙 |

---

## 월별 계획

### 2026-09 — 정리와 기초

- 이 저장소 정리 (완료)
- CS:APP 1~3장
- Bomb Lab — **정답 찾기가 아니라 x86-64 + GDB 사고방식 확보가 목표**
- CV 초안

### 2026-10 — 메모리와 익스플로잇

- CS:APP Attack Lab
- OSTEP — Processes · Address Spaces · Paging
- Security Engineering (Ross Anderson) 시작
- 산출물: `systems-security-lab` 저장소 개설

### 2026-11 — 바이너리와 sanitizer

- OSTEP concurrency
- Practical Binary Analysis · pwn.college
- **자작 C/C++ 패킷 파서** 제작 → ASan/UBSan 으로 버그 재현
- 산출물: ELF 분석 · GDB write-up · sanitizer 리포트 · 회귀 테스트

### 2026-12 — Fuzzing

- libFuzzer → AFL++
- 같은 파서를 두 도구로 fuzzing 하고 **실측값만** 비교
  (executions/sec · coverage · time-to-first-crash · unique failures)
- 산출물: fuzzing 리포트 · 재현 가능한 실험

### 2027-01 — RoboSec 착수

- 시스템 경계 · 위협 모델 · 공격면 · 안전 불변식 (**초안은 이미 작성됨**)
- harness 설계
- 산출물: 첫 harness

### 2027-02 — RoboSec 실험

- fuzzing · fault injection · 결과 수집 · 분석
- 산출물: 실험 스크립트 · 재현 가능한 결과 · technical report v1

---

## 주간 루틴 (주 20시간 기준)

| 시간 | 항목 |
|---|---|
| 6h | CS:APP / OSTEP |
| 6h | Lab / 실습 |
| 3h | Security Engineering / 논문 |
| 3h | grippers / RoboSec |
| 2h | README / write-up / 정리 |

시간이 부족하면 비율을 유지하며 전체를 줄입니다.

> **공부 : 실습 ≥ 1 : 1**

---

## 앞으로 만들 저장소

지금 만들지 않는 이유는 하나입니다 — **빈 저장소가 프로필에 여러 개 떠 있는
것이 하나도 없는 것보다 나쁩니다.** 내용이 생긴 뒤에 만듭니다.

### robosec

ROS 2 로봇 시스템의 상태 인지 보안 테스팅. crash 가 아니라 **물리 안전 불변식의
위반**을 찾습니다. 위협 모델과 불변식은 [`robosec/`](robosec/) 에 이미 있습니다.

### systems-security-lab

CS:APP · OSTEP · 바이너리 분석 · sanitizer · fuzzing.

**공개 정책을 먼저 정해 둡니다** — 공식 lab 의 정답이나 exploit 페이로드는
공개하지 않습니다. CMU 15-213 의 Bomb/Attack Lab 은 매 학기 실제 수업에서
쓰이므로 정답 공개는 그 수업을 망칩니다. 대신 **분석 과정**과 **직접 만든 취약
프로그램**으로 같은 내용을 재현합니다. 포트폴리오로도 그쪽이 낫습니다 —
"주어진 문제를 풀었다" 보다 "같은 취약점을 스스로 만들고 관찰하고 고쳤다" 가
더 많은 것을 보여줍니다.

### udp-network-lab

UDP 응용 프로토콜을 직접 설계하고 손실·중복·재정렬·손상 아래에서 계측합니다.
2023년 5G/UDP 경험을 **검증 가능한 형태로** 다시 만드는 것이 목적입니다.

프레임에 `magic · version · sequence_number · timestamp · message_type ·
payload_length · payload · checksum` 을 두고, **필드마다 왜 필요한지** 씁니다.
grippers 의 Host↔Pi 링크에는 `sequence_number` 와 `timestamp` 가 없으므로,
이 저장소는 그 부재가 무엇을 뜻하는지 보여주는 대조군이기도 합니다.

여기서 만든 파서는 `systems-security-lab` 의 **fuzzing 대상**으로도 씁니다 —
같은 코드가 네트워킹 포트폴리오이자 fuzzing 타깃입니다.

### cryptography-lab

보조 트랙. Cryptopals Set 1~3 → TLS/PKI. 학부의 유한체·군·지표 배경과 잇되,
**주력을 흐리지 않는 선까지만** 합니다.

---

## 두 갈래의 표현 차이

기술 기반은 하나이고, 마지막 표현만 다릅니다.

| | 대학원 | 취업 |
|---|---|---|
| 핵심 질문 | **Why?** | **How?** |
| 강조 | 연구 문제 · 방법 · 실험 | 구현 · 디버깅 · 검증 |
| grippers | research testbed | 대표 시스템 |
| RoboSec | 대표 연구 프로젝트 | Reliability/Security 프로젝트 |
| Technical report | 중요 | 선택 |
| README · 측정 결과 | 중요 | **매우 중요** |

- **대학원:** Research Question → Method → Experiment → Result
- **취업:** Problem → Implementation → Debugging → Verification → Result
