# SmolVLA — Intel Arc(XPU)에서 VLA 파인튜닝

> *2026 · 단독 · 로봇팔 트랙 확장(오프라인)*
>
> [SO-ARM101 트랙](soarm-robotarm-track.md)에서 "미도달"로 남겨 둔 **VLA(Vision-Language-Action)**를,
> 실기 팔 없이 **오프라인 파인튜닝**으로 실제로 돌려 본다. NVIDIA/CUDA가 아니라 **Intel Arc
> B580 GPU(XPU)** 위에서 SmolVLA가 수렴함을 실측으로 보인다.

---

## Problem

VLA는 보통 CUDA 전제로 이야기되지만, 이 트랙의 학습 자원은 **Intel Arc GPU**다. 두 질문:
(1) SmolVLA 파인튜닝이 XPU에서 실제로 되는가? (2) [redball 데이터셋](lerobot-imitation.md)으로
얼마나 수렴하는가?

## Method

- 모델: `lerobot/smolvla_base` (총 450M, 학습가능 100M) 파인튜닝.
- 데이터: [`kica927/redball`](https://huggingface.co/datasets/kica927/redball) — 15 에피소드 /
  8,645 프레임, 언어 task "pick up the red ball and place it somewhere".
- **핵심 함정:** SmolVLA base 는 카메라 키를 `camera1` 로 기대하는데 redball 은 `followcam` →
  `--rename_map='{"observation.images.followcam":"observation.images.camera1"}'` 필수.
- 실행: `--policy.device=xpu`, batch 4, 6000 step, lerobot 0.6.1 · **torch 2.11.0+xpu**.

## Results

**Intel Arc B580 XPU에서 SmolVLA 파인튜닝 완료** — ~9.8 step/s, 6000 step ≈ **12분**.

| step | 50 | 500 | 1000 | 2000 | 3000 | 5000 | 6000 |
|---|---|---|---|---|---|---|---|
| loss | 0.615 | 0.364 | 0.274 | 0.200 | 0.138 | 0.099 | **0.096** |

깨끗한 단조 수렴(0.615 → 0.096). 체크포인트 3000·6000 저장.

## Findings

- **VLA 학습에 CUDA가 필수는 아니다.** `torch.xpu` 백엔드로 Arc B580에서 SmolVLA(450M)가
  문제없이 파인튜닝된다 — "SmolVLA=NVIDIA 필요"라는 통념을 실측으로 반증.
- 학습 자체는 **하드웨어(로봇 팔) 없이 성립** — 데이터셋만 있으면 된다. 실기가 필요한 것은
  롤아웃(정책을 실제 팔에서 구동)뿐이다.

## Limitations

- **롤아웃(실기 추론) 미수행** — 실기 SO-ARM101 팔이 없어 학습·수렴까지만 검증했다. 정책이
  실제로 공을 집는지는 별개 검증이며, 하드웨어 접근이 2026-09-08 에 끝나므로 그 전 과제.
- 데이터가 **단일 과제·단일 지시문**(빨간 공 1종)이라, VLA의 언어 일반화 이점은 이 데이터로는
  드러나지 않는다. 의미 있는 VLA 결과엔 다양한 물체·지시가 필요(다음 단계).
- loss 수렴은 학습 신호일 뿐, 실기 성공률과 직접 등가가 아니다.

## Future Work

(1) 실기 롤아웃으로 성공률 측정, (2) 멀티태스크·다양한 언어 지시로 데이터 확장,
(3) ACT vs SmolVLA 동일 데이터 비교(오프라인 지표).

## 재현
데스크탑 `~/smolvla_ft.sh` (XPU 파인튜닝 명령). 체크포인트는 용량상 저장소 제외
(`~/smolvla_redball_ft/checkpoints/`).
