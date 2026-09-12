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

## 재실험 — 클래스 균형 재샘플링 (2026-09-12)

첫 결과(mAP50 0.050)의 원인을 실제로 세어 확인했다: 무작위 1,000장 서브셋에 **rider
90개·bicycle 130개·motorcycle 51개·train 단 1개**(인스턴스 수)뿐이었다 — mAP 0.0이
나온 게 당연했다.

**샘플링을 다시 짰다.** 원본 10,000장 중 희귀 4클래스(rider·bicycle·motorcycle·train)가
하나라도 있는 이미지는 912장(9.12%)뿐이다. 이 912장을 전량 포함하고 나머지를 무작위로
채워 **3,000장**(기존의 3배)을 구성했다 — 전체 10,000장을 다 쓰면 학습 시간이 8시간대로
늘어 포트폴리오 시간 예산을 넘기므로, "희귀 이미지 비중을 원본 대비 3배 이상 오버샘플링
하면서 학습 시간은 3배 선으로 억제"하는 절충점으로 3,000장을 택했다. train 2,400 / val 600,
같은 40 epoch, Arc B580.

**Before / After**

| 지표 | 1,000장(무작위) | 3,000장(균형) |
|---|---|---|
| mAP50-95 | 0.031 | **0.181**(5.8배) |
| mAP50 | 0.050 | **0.349**(7.0배) |
| precision | 0.555 | 0.605 |
| recall | 0.059 | **0.328**(5.6배) |
| 학습 시간 | 49분 | 71분 |

클래스별 mAP50(균형 후): car 0.397 · truck 0.315 · bus 0.246 · traffic sign 0.199 ·
pedestrian 0.197 · motorcycle 0.127 · traffic light 0.122 · bicycle 0.120 ·
**rider 0.092 · train 0.000(그대로)**.

**train 클래스는 데이터셋 자체의 한계다.** 3,000장으로 늘려도 train 인스턴스는 15개뿐이었다
(원본 10,000장 안에 기차가 거의 없다 — BDD100K validation split의 특성). 오버샘플링으로
해결되는 문제가 아니라, 이 공개 데이터셋 자체에 train 클래스 학습이 성립하지 않는다는
뜻이다.

## (B) CARLA — 헤드리스 실행 검증 (2026-09-12)

`./CarlaUE4.sh -RenderOffScreen -vulkan -quality-level=Low`으로 서버를 실제로 띄우고
Python API로 접속해 검증했다.

| 항목 | 결과 |
|---|---|
| 헤드리스 기동 | **성공** — DISPLAY 없이 `-RenderOffScreen`으로 정상 구동, 종료도 SIGTERM으로 정상 처리(exit 143) |
| 기본 시나리오 | 차량 스폰 + 오토파일럿 주행 + 카메라 센서로 프레임 10장 캡처 성공 |
| 인지 모델 연결 | (A)의 파인튜닝 YOLO로 캡처한 CARLA 프레임 10장 추론 → **10장 전부에서 검출**(주로 car·pedestrian·traffic sign, 프레임당 1~3건) |

→ **시뮬레이터 → 인지 모델 최소 폐루프가 실제로 동작한다.** Immortan에서 규칙기반으로
했던 "카메라 → 판단"의 학습 기반 버전을 시뮬레이터 안에서 재현한 첫 단계다.

## Findings

1. **mAP 0.0의 원인은 추측이 아니라 실측으로 확정됐다.** rider 90·bicycle 130·
   motorcycle 51·**train 1**개(1,000장 기준 인스턴스 수)뿐이었던 것이 원인이었고,
   희귀 클래스를 오버샘플링하자 즉시 개선됐다(mAP50 0.050→0.349, recall 0.059→0.328).
   "데이터가 없으면 학습이 안 된다"는 당연한 명제를, 숫자를 실제로 세어서 확인한
   사례다.
2. **오버샘플링에도 한계가 있다.** train 클래스는 3배로 늘려도 인스턴스 15개뿐이라
   mAP가 여전히 0.0이다 — 이 데이터셋(BDD100K validation split 미러) 자체에 기차가
   거의 없다. 재샘플링으로 못 고치는 문제와 고칠 수 있는 문제를 구분해야 한다.
3. **precision(0.605)은 거의 그대로인데 recall(0.328)만 크게 뛰었다** — 데이터가
   늘면서 모델이 "놓치던 것"을 더 잡아내기 시작했다는 뜻이다. [A2](a2-synthetic-gap.md)에서
   본 "학습량 증가는 특히 recall을 메운다"는 패턴이 여기서도 재현됐다.
4. **CARLA는 다운로드·압축뿐 아니라 실제 구동까지 이 하드웨어에서 문제없다.** Intel
   Arc B580 + Vulkan 오픈소스 드라이버 조합으로 UE4 기반 시뮬레이터가 헤드리스로
   정상 기동했고, 캡처한 프레임에 인지 모델을 그대로 물릴 수 있었다 — 병목이었던
   적이 애초에 없었다.

## 정직한 한계

- **train 클래스는 이 데이터셋으로는 풀리지 않는다.** 오버샘플링을 아무리 해도 원본에
  있는 절대량(15개) 이상은 만들어낼 수 없다 — 다른 데이터 소스가 필요한 문제로 남긴다.
- **CARLA 검증은 "기동·프레임 캡처·추론 연결"까지다.** 실제 폐루프 제어(인지 결과로
  차량을 조향하는 것)는 하지 않았다 — Future Work로 남긴다.
- **CARLA 프레임 10장은 매우 작은 표본이다.** "10장 전부 검출됨"은 파이프라인이 도는지
  확인한 것이지, 시뮬레이션 이미지에 대한 정량적 정확도(mAP 등)를 보인 것이 아니다 —
  CARLA 프레임엔 애초에 정답 라벨이 없어 mAP 자체를 낼 수 없다.
- **Immortan과는 다른 문제를 다뤘다**, 우열 비교가 아니다. Immortan은 팀이 만든
  규칙기반 파이프라인의 실기 검증(대회 1등)이고, 이 프로젝트는 개인이 공개
  데이터·시뮬레이터만으로 인지·환경을 갖추는 실험이다. 서로 대체하지 않는다.
- 사전학습(COCO) 가중치 자체의 BDD 클래스에 대한 zero-shot 성능을 별도로 재지
  않았다 — 파인튜닝의 순수 기여분(사전학습 대비 개선폭)은 이 결과만으로는 분리되지
  않는다.

## Future Work

- ~~BDD100K 서브셋 규모 확대 + 클래스 균형 확인 후 재학습~~ → **완료.** mAP50
  0.050→0.349. train 클래스만 데이터셋 자체 한계로 남음(위 참고).
- ~~CARLA 헤드리스 실행 검증과 기본 시나리오~~ → **완료.** 프레임 캡처 + YOLO 추론
  연결까지 확인.
- 이 인지 모델을 CARLA와 실시간으로 묶어 **폐루프 제어**(인지 결과로 조향/제동)까지
  구현 — 이번엔 정적 프레임 추론만 했다.
- train 클래스를 위해 다른 공개 데이터셋(철도 포함 소스)을 추가로 찾아 보강.

## 코드

`code/edge-perception-desktop/` — `prepare_bdd_subset.py`(1차, 무작위 1,000장),
`prepare_bdd_subset_balanced.py`(2차, 희귀 클래스 우선 3,000장), `train_yolo.py`/
`train_yolo_balanced.py`(파인튜닝 + mAP 평가), `metrics.json`/`metrics_balanced.json`(1차·2차 결과),
`carla_connection_test.py`(헤드리스 서버 접속 검증), `carla_basic_scenario.py`(차량
스폰·오토파일럿·카메라 캡처), `infer_on_carla_frames.py`(캡처 프레임에 YOLO 추론).
