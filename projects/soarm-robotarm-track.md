# SO-ARM101 로봇팔 트랙 — 시뮬레이션에서 모방학습까지

> Intel Physical AI 교육의 로봇팔 과정을 **단계적으로 올라간 기록**. 각 단계가
> 앞 단계의 산출물을 재사용해 다음으로 확장된다. 시뮬 제어 → 규칙기반 비전
> Pick&Place → 안전 설계 → **모방학습(LeRobot)**, 그리고 VLA는 하드웨어 종료로
> 미도달.
>
> 하드웨어: SO-ARM101 (STS3215 시리얼 버스 서보 · 데이지체인) · HP60C 카메라

이 문서는 **개요**다. 두 단계는 자체 문서가 있다:
- [색상별 컵 정렬 (Step5 FINAL)](cup-sorting.md)
- [LeRobot 모방학습](lerobot-imitation.md)

---

## 왜 트랙으로 묶어 보는가

개별 과제로 흩어 놓으면 "여러 개를 했다"로 읽히지만, 실제로는 **하나의 팔로
같은 도구를 쌓아 올린 한 줄기**다. 뒤 단계가 앞 단계의 코드·데이터·캘리브레이션을
그대로 물려받는다. 그 연속성이 이 트랙의 핵심이다.

## 단계

| 단계 | 배운 것 | 산출물 | 상태 |
|---|---|---|---|
| **1–2. 기초** | STS3215 서보·데이지체인, 좌표계, **FK(POE)/IK** | 노트 | ✅ |
| **3–4. MuJoCo** | 물리 엔진 시뮬 + SO-ARM 제어(`qpos`/`ctrl`) | 시뮬 실습 | ✅ |
| **5. 비전 — 공 분류** | HSV 검출 · **호모그래피**(pixel→robot) · Pick&Place | `개발문서_공분류` + 코드 | ✅ |
| **5. 비전 — 컵 정렬 (FINAL)** | 위를 재사용 + **안전 3종**(E-STOP·지연·한계거부) | [문서](cup-sorting.md) · `cup_stacking.py` | ✅ |
| **6. 모방학습 (LeRobot)** | 텔레오퍼레이션 녹화 → 학습(ACT·SmolVLA) → 추론, HF 업로드 | [문서](lerobot-imitation.md) · [`kica927/redball`](https://huggingface.co/datasets/kica927/redball) | ✅ |
| **7. VLA** | Vision-Language-Action (OpenVLA·Pi0·SmolVLA) | 이론만 | ⛔ 미도달 |

## 각 단계가 어떻게 물려받는가

### 시뮬(MuJoCo) → 실기(SO-ARM101)

FK 를 **POE(Product of Exponentials)** 로 세우고 IK 는 반복해 푼다. MuJoCo 에서
`qpos`(관절 상태)와 `ctrl`(제어 입력)의 차이를 익힌 뒤 실물로 넘어갔다. 교육용
`soarm_lab` 라이브러리(`arm.py`·`ik_core.py`·`fk_core.py`·`real.py`·`grasp.py`)가
시뮬과 실물을 같은 인터페이스로 감싼다 — 뒤 단계가 전부 이걸 쓴다.

### 공 분류 → 컵 정렬 (같은 코드, 대상만 교체)

공 분류에서 만든 것을 컵 정렬이 그대로 물려받았다. **`grasp.approach_xy()` 의
반지름만 공→컵으로 바꾸고**, HSV 임계값만 다시 잡으면 됐다. 새로 짠 것은 컵
스택의 **높이 갱신 로직**(집을수록 소스가 줄고 목적지가 는다)과 **안전 계층**뿐이다.

여기서 만든 안전 3종 — 긴급정지(전 서보 토크 OFF), **지연 시 새 명령 정지**,
도달 불가 좌표 거부 — 가 이 트랙에서 가장 값진 산출물이고, 나중에
[grippers](grippers.md) 의 안전 설계로 이어진다.

### 규칙기반 → 학습기반 (LeRobot)

앞의 비전 Pick&Place 는 **사람이 규칙을 짰다**(HSV·호모그래피·IK). LeRobot 단계는
반대로 **사람이 시범을 보이고 정책이 규칙을 배운다.** leader 팔로 조종하면 follower
팔이 따라 하며 카메라·관절상태·액션을 30fps 로 녹화한다.

- 데이터셋 [`kica927/redball`](https://huggingface.co/datasets/kica927/redball) —
  **15 에피소드 · 8,645 프레임 · 30 fps**, `robot_type: so_follower`
- Physical AI Studio 로 모아 LeRobot v3.0 형식으로 옮기고 **Hugging Face 에 공개 업로드**
- ACT 와 SmolVLA 두 정책을 학습

같은 대상(빨간 공)을 **규칙으로도, 학습으로도** 다뤄 본 것이 이 트랙의 대비점이다.

## VLA — 왜 미도달인가 (정직하게)

트랙의 마지막 계단은 VLA(Vision-Language-Action) — 이미지+언어를 받아 **action
token 을 직접 출력**하는 모델(OpenVLA·Pi0·SmolVLA)이다. **이론까지만 배우고
실습은 못 했다.** 2026-09-08 하드웨어 사용 종료가 먼저 왔다.

이걸 배운 것이 [grippers 캡스톤의 정직한 서술](grippers.md)로 이어진다 — grippers
는 "end-to-end VLA 가 아니다"라고 명시한다. 모듈 간에 오가는 것이 학습된 특징
벡터가 아니라 심볼(`toy`·`BLUE`)이기 때문이다. **VLA 가 무엇인지 알기 때문에
그것이 아니라고 정확히 말할 수 있다.**

## Limitations

- **비전 단계의 파라미터 상당수가 실측이 아니라 현장 조정값**이다(HSV·`GRIP_Z`·`Z_HOVER`).
- **LeRobot 정책의 성공률을 재지 않았다.** 수집 규모(15ep·8,645프레임)는 데이터셋
  메타에 있지만, 그것은 성공률이 아니다.
- **VLA 미도달** — 이론만.
- 규칙기반 비전은 **단일 조명·고정 배치 전제**라 조도가 바뀌면 HSV 가 깨진다
  (공 분류 문서의 문제해결 절에 이 한계와 대응이 적혀 있다).

## 산출물 한눈에

| 단계 | 산출물 |
|---|---|
| 비전 공 분류 | `개발문서_공분류` (338줄, 문제해결 과정 포함) + LeRobot 데모 데이터 |
| 컵 정렬 | [`cup-sorting.md`](cup-sorting.md) · `cup_stacking.py`(320줄) · `calibrate_homography.py` |
| 모방학습 | [`lerobot-imitation.md`](lerobot-imitation.md) · [`kica927/redball`](https://huggingface.co/datasets/kica927/redball) |
| 재사용 라이브러리 | 교육용 `soarm_lab` (시뮬/실물 공통 인터페이스) |
