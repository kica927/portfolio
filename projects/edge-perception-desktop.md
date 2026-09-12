# Edge Perception Desktop — 공개 데이터셋 인지모델 + CARLA (Intel Arc B580)

> *2026-09 · 단독 · 데스크탑(Intel Arc B580) 자율주행 트랙*
>
> [Immortan](immortan-self-driving.md)(MentorPi 실기, 팀 프로젝트, 규칙기반 인지·제어)과는
> **독립적인** 자율주행 미니 프로젝트다. 여기서는 실기 로봇 없이, 공개 데이터셋으로
> 학습한 인지 모델과 시뮬레이터(CARLA)를 이 데스크탑 단독 자원(Arc B580, CUDA 없음)으로
> 다룬다.

---

## Problem

Immortan은 팀이 만든 규칙기반 파이프라인을 실기 메카넘 로봇에서 검증한 프로젝트였다.
이 프로젝트는 반대 축을 본다 — **실기가 전혀 없을 때, 공개 데이터와 시뮬레이터만으로
자율주행 인지·환경을 어디까지 혼자 갖출 수 있는가.** 두 갈래로 나눠 확인한다.

- (A) 공개 자율주행 데이터셋으로 인지 모델(차량·보행자·신호 탐지)을 파인튜닝
- (B) CARLA 시뮬레이터를 이 GPU(디스크리트, CUDA 아님)에서 실제로 띄울 수 있는가

## Method

**(A) 인지 모델**
- 데이터: [HuggingFace `dgural/bdd100k`](https://huggingface.co/datasets/dgural/bdd100k)
  (BDD100K validation split의 FiftyOne 미러, BSD, 로그인 불필요). 원본 10,000장(695MB)
  중 **1,000장을 무작위 추출**(seed=42) → train 800 / val 200.
- 클래스 10종: car·truck·bus·pedestrian·rider·bicycle·motorcycle·traffic light·
  traffic sign·train (BDD100K 표준에서 극희귀 3종 — other vehicle·trailer·other
  person — 제외).
- 라벨 포맷 변환: FiftyOne의 `bounding_box`(좌상단 x,y,w,h)를 YOLO 포맷(중심 xc,yc,w,h,
  정규화)으로 직접 변환.
- 모델: YOLO11n, COCO 사전학습 → BDD 10클래스로 40 epoch 파인튜닝. `torch.xpu`(Arc B580),
  PyTorch 2.14+xpu 공식 wheel.

**(B) CARLA**
- 먼저 `vulkaninfo`로 Arc B580의 Vulkan 지원 여부를 확인(CARLA는 UE4 Vulkan RHI로
  구동).
- 공식 CDN에서 `CARLA_0.9.15.tar.gz`(8.39GB)를 nohup 백그라운드로 다운로드 후 압축 해제.

## Results

**(A) 인지 모델 — 정량 지표(val 200장)**

| 지표 | 값 |
|---|---|
| mAP50-95 | 0.031 |
| mAP50 | 0.050 |
| mAP75 | 0.029 |
| precision(평균) | 0.555 |
| recall(평균) | 0.059 |
| 학습 소요시간(40 epoch) | 49분(2,940초) |

클래스별 mAP50: car 0.059 · bus 0.130 · pedestrian 0.036 · traffic sign 0.031 ·
truck 0.017 · traffic light 0.006 · **rider·bicycle·motorcycle 0.000**.

- 추론 속도(Arc B580): 전처리 1.3ms + 추론 12.9ms + 후처리 29.8ms.

**(B) CARLA**

| 항목 | 결과 |
|---|---|
| Vulkan | API 1.4.318, Arc B580(discrete GPU) 정상 인식, Mesa 오픈소스 드라이버 25.2.8 |
| 다운로드 | 8.39GB, 실측 80.9MB/s, **99초** 만에 완료 |
| 압축 해제 | 19GB, 자동 완료(`CarlaUE4-Linux-Shipping` 실행파일 확인) |

## Findings

1. **40 epoch·800장으로는 BDD100K 10클래스 파인튜닝이 크게 부족하다.** mAP50 0.050은
   실전 배포와는 거리가 멀다. 빈도가 높은 클래스(bus 0.130, car 0.059)는 약한 신호라도
   있지만, rider·bicycle·motorcycle은 정확히 0.0 — 서브셋 안에 해당 클래스 샘플이
   극히 적었을 가능성이 크다(클래스 분포를 확인하지 않고 무작위 샘플링만 했다).
2. **precision(0.555)이 recall(0.059)보다 훨씬 높다** — 모델이 "확신할 때만 예측"하는
   보수적인 상태다. 예측한 것 중 절반 이상은 맞지만, 대부분을 놓친다. [A2](a2-synthetic-gap.md)에서도
   본 "학습량 부족 시 recall이 먼저 무너진다"는 패턴과 같은 방향이다.
3. **병목은 하드웨어가 아니라 데이터/학습량이다.** 추론 자체는 Arc B580에서 12.9ms로
   충분히 빠르다 — GPU가 남아도는데 정확도가 낮다는 것은 더 많은 데이터·에폭으로
   풀어야 할 문제라는 뜻이다.
4. **CARLA 같은 대형 시뮬레이터 자산도 이 환경에서는 병목이 아니다.** 8.4GB를 99초에
   받고 19GB로 푸는 데 걸린 시간이 인지 모델 학습(49분)보다 훨씬 짧다 — 시간을 써야
   할 곳은 시뮬레이터 설치가 아니라 데이터·모델 쪽이라는 우선순위가 실측으로 드러난다.

## 정직한 한계

- **mAP50 0.050은 낮은 수치이며, 그대로 인용하면 안 된다.** 40 epoch·800장이라는
  작은 스케일이 주 원인으로 보이나, 클래스 불균형(무작위 샘플링만 하고 클래스별
  샘플 수를 세어보지 않았다)도 함께 작용했을 가능성이 있다 — 두 원인을 분리하지
  않았다.
- **CARLA는 다운로드·압축 해제만 검증했다.** `CarlaUE4.sh -RenderOffScreen -vulkan`
  실행 자체는 이번 작업 범위 밖이었다 — "설치됨"과 "헤드리스로 돌아감"은 다른
  주장이며, 후자는 아직 확인되지 않았다.
- **Immortan과는 다른 문제를 다뤘다**, 우열 비교가 아니다. Immortan은 팀이 만든
  규칙기반 파이프라인의 실기 검증(대회 1등)이고, 이 프로젝트는 개인이 공개
  데이터·시뮬레이터만으로 인지·환경을 갖추는 실험이다. 서로 대체하지 않는다.
- 사전학습(COCO) 가중치 자체의 BDD 클래스에 대한 zero-shot 성능을 별도로 재지
  않았다 — 파인튜닝의 순수 기여분(사전학습 대비 개선폭)은 이 결과만으로는 분리되지
  않는다.

## Future Work

- BDD100K 서브셋 규모 확대(1,000 → 더 많이) + 클래스 균형을 먼저 확인한 뒤 재학습.
- CARLA 헤드리스 실행(`-RenderOffScreen`) 검증과 기본 시나리오(차선 유지 등) 스크립트.
- 이 인지 모델을 CARLA 카메라 입력에 연결해 폐루프(perception → control) 검증 —
  Immortan에서 규칙기반으로 했던 것을 학습 기반으로 다시 해보는 다음 단계.

## 코드

`code/edge-perception-desktop/` — `prepare_bdd_subset.py`(HF에서 1,000장 추출 + YOLO
라벨 변환), `train_yolo.py`(파인튜닝 + mAP 평가), `metrics.json`(평가 결과 원본).
