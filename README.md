# 조현우 · Portfolio

수학과 전자공학에서 출발해 **통신 시스템 → 로봇 시스템 → 시스템 보안**으로
가고 있습니다.

관심 분야는 **네트워크로 연결된 사이버-물리 시스템의 소프트웨어·시스템 보안**
입니다 — 특히 로봇과 임베디드 플랫폼.

```
Mathematics · Finite Fields
          ↓
Electronic Engineering
          ↓
5G / UDP Communication
          ↓
Linux · ROS 2 · Physical AI
          ↓
Software / Systems Security
          ↓
Robotic & CPS Security
```

---

## 프로젝트

### 🤖 [Grippers — ROS 2 분산 모바일 매니퓰레이터](projects/grippers.md)
*2026 · 팀 6인 · Intel Physical AI 과정 캡스톤*

Host PC 가 좌표와 경로를, Raspberry Pi 가 물리 실행과 안전 집행을 소유하는 2대
구성. **Pi 측 전체**(미션 FSM · 주행 · 파지 · 투입 · 통신)를 담당했습니다.

제어 주기 **1.6 Hz → 9.6 Hz** · 6클래스 파지→투입 실기 검증 · 테스트 422개 ·
CI 가 매 push 마다 Fake 어댑터로 전 미션 파이프라인 실행

→ 코드 [`grippers-intel/grippers`](https://github.com/grippers-intel/grippers) ·
[개인 미러](https://github.com/kica927/grippers)

### 👁️ [Grippers 인지 파이프라인 — 합성 데이터 → 엣지 추론](projects/grippers-perception.md)
*2026 · 팀 3인 · Intel AI Festival 중간보고*

실사진 **0장**. Houdini 로 장면을 절차적으로 생성해 라벨까지 자동으로 뽑고,
Intel Geti → OpenVINO → **Hailo-10H** 로 엣지까지 내렸습니다. 검출을 그대로
믿지 않기 위해 신뢰도와 **독립인** 화면위치 게이트를 붙였습니다.

Hailo **76.5 FPS** (CPU 폴백 14.3, 요구치 5.0) · 210초 녹화 실측 **검출 12개 중
통과 0개** — 검출률이 아니라 게이트가 병목임을 분리해 냄

### 🍎 [grippers-host-mac — Apple Silicon 이식](projects/grippers-host-mac.md)
*2026 · 단독*

Windows 전용 Host 스택에서 DirectShow 의존을 걷어내고 OpenVINO/geti-sdk 가
arm64 에서 도는 것을 확인했습니다.

추론 **364 ms → 130 ms** · 루프 **7.0 Hz → 9.6~10.1 Hz** · Windows 동작은 불변

→ 코드 [`kica927/grippers-host-mac`](https://github.com/kica927/grippers-host-mac)

### 🏎️ [Immortan — 자율주행 대회 🥇 1등](projects/immortan-self-driving.md)
*2026 · 팀 6인 · 과정 내 대회*

MentorPi 메카넘 로봇으로 차선추종 · 코너링 · 횡단보도 · 신호등 · 우회전 · 주차를
자율 수행. **우선순위를 조건문이 아니라 메인 루프 구조로** 보장했습니다 —
정지 판단이 차선추종보다 먼저 오므로 *"멈출 이유가 없을 때만 달린다"* 가
코드 배치로 강제됩니다.

**전 브랜치 430커밋 중 80건** · `kica927/right` 브랜치 +695/−319줄

→ 코드 [`grippers-intel/Immortan-Project`](https://github.com/grippers-intel/Immortan-Project)

### 🔬 [Intel Geti — F1 차량 팀 분류](projects/geti-f1-classification.md)
*2026 · 단독*

같은 400장으로 **Detection 58% → Segmentation 91%.** 데이터를 늘려서가 아니라
**라벨 형태만 바꿔** 얻은 33%p 입니다. "데이터가 부족하다"는 가설이 틀렸다는 것을
변수를 하나만 바꿔 확인했습니다.

### 🦾 [LeRobot — SO-ARM101 모방학습](projects/lerobot-imitation.md)
*2026 · 단독*

리더암 시범을 녹화해 **ACT · SmolVLA(VLA)** 정책을 학습하고, 팔로워암을 단독
구동. record → train → rollout 전 구간이 돕니다.
*(성공률은 측정하지 못했고, 그 점을 한계로 적었습니다.)*

### 🦾 [SO-ARM101 로봇팔 트랙 — 시뮬에서 모방학습까지](projects/soarm-robotarm-track.md)
*2026 · Intel 로봇팔 교육 · 단계적 진행*

MuJoCo 시뮬 제어 → 규칙기반 비전 Pick&Place(공 분류·컵 정렬) → **LeRobot 모방학습**
([`kica927/redball`](https://huggingface.co/datasets/kica927/redball) 공개, 15ep·8,645프레임)
→ VLA(미도달). 한 팔로 같은 도구를 쌓아 올린 한 줄기입니다. 아래 컵 정렬·LeRobot 은
이 트랙의 개별 단계 문서입니다.

### 🥤 [색상별 컵 정렬 — SO-ARM101 미니 프로젝트](projects/cup-sorting.md)
*2026 · 로봇팔 교육 FINAL 과제 · 안전/시스템 담당*

색이 섞인 컵 6개를 카메라로 색 인식해 색상별로 재적재. **안전 계층**을 맡았습니다 —
긴급정지(전 서보 토크 OFF), **지연 시 새 명령 정지**(모르면 안 움직임),
도달 불가 좌표 거부. grippers 로 이어지는 안전 사고가 여기서 시작됐습니다.

### 📡 [5G/UDP 종단간 통신 프로토타입](projects/5g-udp-prototype.md)
*2023 · 쉴드론 인턴*

철도 차량 간 이동통신. RS-232 → Serial-to-Ethernet → UDP/IP → 5G 모뎀 →
멀티캐스트/프록시 → 원격 단말. 패킷 프로토콜 분석·구현, PacketSender/Wireshark 디버깅.

당시 로그를 3년 뒤에 다시 읽어 **왕복 30~40 ms · 첫 패킷 12.2 초**(모뎀 세션 수립)를
분리해 냈고, 남아 있던 오류 주입 시험표에서 **CRC32·시퀀스·발신자 ID 가 전부
검사되지 않는다**는 것을 확인했습니다. 그때는 "동작한다"로 읽은 표가 지금은
위협 목록으로 읽힙니다. *(코드·원자료 비공개 — 회사 자산, 실제 운영 IP 포함)*

### 📐 [유한체 위의 Pell 방정식 해집합](projects/pell-equations.md)
*2022 · 학부 독립 연구 · 학술제 최우수상*

해집합에 아벨군 구조를 세우고, 곱셈 지표와 Jacobi 합으로 그 크기를 다뤘습니다.

---

## 다음 — [RoboSec](plans/robosec/)

> 조작되거나 손상된 Host 명령이 ROS 2 기반 로봇 시스템에서 **안전하지 않은
> 상태 전이**를 일으킬 수 있는가?

기존 fuzzer 는 crash 를 찾습니다. 로봇 제어에서 crash 는 오히려 안전한 실패입니다 —
프로세스가 죽으면 명령이 끊기고 워치독이 돕니다. 정말 위험한 것은 **crash 없이
계속 도는 상태**입니다.

**RoboSec 는 crash 가 아니라 물리·상태 안전 불변식의 위반을 찾습니다.**

대상은 제가 직접 만든 위 로봇 시스템입니다. 시스템을 만든 사람이 그 위협 모델을
쓴다는 것이 전제입니다 — **어디에 방어층이 있고 왜 거기 있는지 알고 시작합니다.**

| | |
|---|---|
| [`threat_model.md`](plans/robosec/threat_model.md) | 신뢰 경계 · 코드에서 확인한 공격면 5건 · **이미 있는 방어층 8건** · 공격자 모델 |
| [`security_properties.md`](plans/robosec/security_properties.md) | 안전 불변식 I1~I8 · 위반 계수 규칙 |

전체 계획은 [`plans/roadmap.md`](plans/roadmap.md) 에 있습니다. 하드웨어 접근이
2026-09-08 에 끝나므로, 이후 실험은 **하드웨어 비의존 도메인 계층을 대상으로 하고
종료 전 녹화한 실기 궤적을 정답지로 삼는** 모델 기반 구성으로 갑니다.

---

## 어떻게 일하는가

**증상이 아니라 계측으로 원인을 찾습니다.**

> 제어 주기가 1.6 Hz 였습니다. 증상은 "Pi 가 명령을 놓친다" 였고, 원인은 E-STOP
> 경로가 매 사이클 0.5초를 블로킹 대기하는 것이었습니다. 로그 타임스탬프 간격이
> 답을 갖고 있었습니다. → **9.6 Hz**

**튜닝으로 못 고치는 문제를 구별합니다.**

> 좌우 정렬 보정이 같은 값으로 9회 반복되고 끝났습니다. 허용오차 격자가 10.5°
> 인데 필요한 보정이 5.2° 였습니다 — 분간해야 할 단위가 격자의 1/4 이라
> **원리적으로 수렴할 수 없는 구성**이었습니다.

**틀린 판단도 기록합니다.**

> macOS 카메라 인덱스를 이름으로 골라야 한다고 적고 그렇게 구현했는데, 실기에서
> 정반대였습니다. 되돌린 과정을 저장소에 남겼습니다.

**측정하지 않은 숫자는 쓰지 않습니다.**

---

## 기술

```
C · C++ · Python
Linux · ROS 2 (Humble) · Docker · Raspberry Pi 5 · 임베디드
UDP/IP · 프로토콜 설계 · Wireshark
OpenCV · OpenVINO · ArUco · 온디바이스 추론 (Hailo)
Git · pytest · CI · GDB · 계측 기반 디버깅
```

**아직 쓰지 않은 도구는 여기 적지 않습니다.** ASan/UBSan · libFuzzer · AFL++ ·
Ghidra 는 [로드맵](plans/roadmap.md)의 일정에 있고, 실제로 쓴 뒤에 올립니다.

---

## 학력 · 자격

- **서강대학교** 수학과 · 전자공학과 복수전공 — 2026-02 졸업
- 전기기사 (2025)
- 2022 수학과 학술제 **최우수상**
- TOEIC 890 · TOEIC Speaking IH(150)

---

## 이 저장소에 대해

각 프로젝트 문서는 같은 틀을 따릅니다 —
**Problem → Architecture → My Contribution → Design Decisions → Implementation →
Problems & Debugging → Verification → Results → Limitations → Future Work.**

틀 자체는 [`templates/`](templates/) 에 있습니다.

**Limitations 절을 비워 두지 않습니다.** 안 해본 것을 안 해봤다고 쓰는 것이
이 저장소의 규칙입니다.

📧 xenon.6830@gmail.com
