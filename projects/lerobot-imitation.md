# LeRobot — SO-ARM101 모방학습 (ACT · SmolVLA)

> 📍 이 프로젝트는 [SO-ARM101 로봇팔 트랙](soarm-robotarm-track.md)의 한 단계입니다.

> **2026-08 · 단독 · Intel Physical AI 과정 Robot Arm 모듈**
>
> 과제: **"테이프를 컵에 끼우기"** — 사람이 리더암으로 시범을 보이고, 그
> 궤적으로 정책을 학습해 팔로워암이 스스로 수행하게 한다.

---

## 1. Problem

로봇 팔에게 작업을 가르치는 두 가지 방법이 있습니다.

| | 방법 | 한계 |
|---|---|---|
| 기존 | 좌표를 계산해 IK 로 푼다 | 물체 위치가 바뀌면 매번 다시 계산 |
| **모방학습** | **사람 시범을 보고 정책을 학습** | 데이터 수집 비용, 일반화 불확실 |

**이 프로젝트는 후자입니다.** 그리고 그 정책이 **VLA(Vision-Language-Action)** —
언어 지시("put the red tape onto the cup")를 받아 행동을 출력합니다.

---

## 2. Architecture

```
리더암(사람이 조작)  ──텔레오퍼레이션──→  팔로워암
         │                                  │
         └──── lerobot-record ──────────────┘
                    ↓
         데이터셋 (HuggingFace 형식 v3.0)
            observation.images.camera1  정면 (C270)
            observation.images.camera2  측면 45° (icspring)
                    ↓
              lerobot-train
              ├─ ACT       처음부터 학습
              └─ SmolVLA   lerobot/smolvla_base 에서 파인튜닝
                    ↓
              lerobot-rollout   ← 리더암 없이 팔로워암 단독 구동
```

---

## 3. My Contribution

`record.sh` · `train_ACT.sh` · `train_SMOLVLA.sh` · `run_model.sh` 네 스크립트를
작성했습니다. **각 스크립트에 함정과 이유를 주석으로 남긴 것이 실질 산출물입니다.**

---

## 4. Design Decisions

### 카메라 키 이름을 체크포인트에 맞춰 지었다

```
camera1 = 정면 (C270)
camera2 = 측면 45° (icspring)
```

> *"키 이름을 `camera1`/`camera2` 로 둔 이유: SmolVLA 체크포인트가 기대하는
> 이름과 같아서 **학습 때 `rename_map` 이 필요 없다.**"*

**데이터를 만들 때 소비처를 미리 맞춘 것**입니다. 안 맞추면 학습 시점에
`rename_map` 으로 매번 번역해야 하고, 그 매핑이 틀리면 feature mismatch 로
죽습니다.

### 단계를 나눴다 — v1(빨강 하나) → v2(3색)

> *"v1 = 빨강 한 개만 (지금). **학습·추론까지 되는 것을 확인한 뒤** v2(3색)로
> 넘어갈 것."*

파이프라인 전체가 도는 것을 먼저 확인하고 규모를 키웁니다. v2 로 갈 때 바꿀 값
(`episode_time_s=75` · `reset_time_s=30` · `num_episodes=80`)도 미리 적어
뒀습니다.

### 두 정책을 비교했다

| | ACT | SmolVLA |
|---|---|---|
| 방식 | Action Chunking with Transformers | VLA 파인튜닝 |
| 출발점 | 처음부터 | `lerobot/smolvla_base` 체크포인트 |
| 언어 지시 | — | **`"put the red tape onto the cup"`** |

**SmolVLA 는 색을 바꿔 3번 실행하면 순서가 완성됩니다** — 정책 하나가 언어로
분기합니다.

### 추론 시 카메라 구성을 학습과 완전히 일치시킨다

> *"`record.sh` 와 **완전히 동일**해야 한다. 키 이름·위치·해상도 모두. 학습 때
> 본 것과 다른 카메라 구성으로 추론하면 성능이 크게 떨어진다."*

---

## 5. Implementation

- **LeRobot** (HuggingFace) · **Intel XPU** (`--policy.device=xpu`)
- 데이터셋 [`kica927/redball`](https://huggingface.co/datasets/kica927/redball) — HuggingFace Hub **공개**, LeRobot v3.0 형식
- 학습 결과 `lsy0284/act_tape` · `outputs/train/smolvla_tape`
- 하드웨어 SO-ARM101 리더/팔로워 2대 · 웹캠 2대

---

## 6. Problems & Debugging

스크립트 주석에 남긴 함정들입니다. **전부 실제로 겪은 것**입니다.

### 6-1. 두 `repo_id` 를 헷갈리면 안 된다

```
--dataset.repo_id   읽어올 데이터셋      (lerobot-record 로 만든 것)
--policy.repo_id    만들어질 모델        (학습 결과물)
```

> *"두 `repo_id` 는 서로 다른 것이니 헷갈리지 말 것."*

### 6-2. 백슬래시 뒤 공백 하나로 학습이 안 돈다

> *"**백슬래시(`\`) 뒤에는 공백조차 오면 안 된다.** 공백이 있으면 줄 연결이
> 끊긴다."*

셸이 조용히 다른 명령으로 해석합니다 — 에러 메시지가 원인을 가리키지 않습니다.

### 6-3. `output_dir` 이 이미 있으면 에러

> *"재학습 시 이름을 바꾸거나 기존 폴더를 삭제할 것."*

### 6-4. feature mismatch 는 에러 메시지가 답을 준다

> *"실행 시 feature mismatch 에러가 나면 **에러 메시지에 체크포인트가 기대하는
> 이름이 찍히므로**, 오른쪽 값을 그것으로 바꿀 것."*

### 6-5. 카메라 대수가 모델에 박혀 있다

> *"예전 redball 모델을 돌리려면 `policy.path` 를 `smolvla_redball` 로 바꾸고
> **카메라를 `camera1` 한 대만 남길 것**(그 모델은 1대로 학습됨)."*

**정책은 학습 시점의 관측 구성을 기억합니다.** 모델을 바꾸면 하드웨어 구성도
같이 바꿔야 합니다.

---

## 7. Verification

`lerobot-rollout` 으로 **리더암 없이 팔로워암 단독 구동**. 색을 바꿔 3회 실행해
순서를 완성하는 것이 목표 시나리오였습니다.

---

## 8. Results

| | |
|---|---|
| 파이프라인 | record → train → rollout **전 구간 동작** |
| 정책 | ACT · SmolVLA 두 가지 학습 |
| 데이터셋 | HuggingFace Hub 공개 — [`kica927/redball`](https://huggingface.co/datasets/kica927/redball) |
| 수집 규모 | **15 에피소드 · 8,645 프레임 · 30 fps** (`robot_type: so_follower`) |
| 텔레오퍼레이션 | leader–follower 이중 팔, 관절별 캘리브레이션(homing_offset·range) |

> 데이터 **수집 규모는 실측**입니다(위 표, `meta/info.json`). 다만 **정량 성공률은
> 측정하지 않았습니다** — 아래 한계 참고. 둘은 다른 값입니다: 얼마나 모았는가와
> 정책이 얼마나 성공하는가.

---

## 9. Limitations

- 🔴 **성공률을 재지 않았습니다.** "된다"는 확인했지만 몇 번 중 몇 번인지
  기록이 없습니다. **이 저장소의 원칙(측정하지 않은 숫자는 쓰지 않는다)에
  따라 성능 수치를 적지 않습니다.** (수집 규모 15ep·8,645프레임은 데이터셋
  메타에 남아 있어 인용했지만, 그것은 성공률이 아닙니다.)
- 🔴 **v2(3색)까지 못 갔습니다** — v1(빨강 하나)에서 하드웨어 사용 기간이
  끝났습니다
- 🟡 ACT 와 SmolVLA 를 **같은 조건으로 비교하지 않았습니다**
- 🟡 카메라 구성 의존이 큽니다 — 재현하려면 위치·해상도까지 맞춰야 합니다

---

## 10. Future Work

**하드웨어 접근이 2026-09-08 에 종료되어 이 프로젝트는 여기서 멈춥니다.**

다시 한다면 먼저 할 것:

1. **에피소드별 성공/실패를 기록**하고 성공률을 낸다
2. ACT vs SmolVLA 를 같은 데이터·같은 에피소드 수로 비교
3. v2 3색으로 확장해 **언어 분기가 실제로 되는지** 확인

> 이 프로젝트에서 얻은 "관측 구성이 정책에 박혀 있다"는 감각은
> [grippers](grippers.md) 의 Ports & Adapters 설계 —
> **어댑터를 바꿔도 도메인이 안 흔들리게** 만든 것 — 과 대비됩니다.
> 학습된 정책은 그 분리가 안 됩니다.
