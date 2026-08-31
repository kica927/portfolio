# A1 — best.pt OpenVINO 엣지 최적화

> *2026 · 단독 · 인텔 교육 스택 부각 트랙*
>
> [grippers 인지 파이프라인](grippers-perception.md)에서 학습한 검출기 `best.pt`를
> **Intel OpenVINO로 변환·INT8 양자화**하고, 정확도·크기·지연을 여러 하드웨어에서
> 측정한다. 학습(Intel Geti) → 변환·양자화(OpenVINO·NNCF) → 추론(Intel CPU·iGPU·Arc)
> 까지 **인텔 엣지 AI 스택 전 과정**을 하나의 정직한 벤치마크로 잇는다.

---

## Problem — "INT8을 쓰면 무조건 빨라지는가?"

엣지 배포에서 INT8 양자화는 표준 처방이지만, 흔한 오해가 있다: **"INT8 = 항상 더 빠름".**
실제로 INT8의 속도 이득은 **타깃 하드웨어에 정수 가속(Intel VNNI/AMX, GPU INT8 경로)이
있느냐**에 종속된다. 이 프로젝트는 같은 INT8 모델을 서로 다른 하드웨어에서 돌려 그 차이를
실측으로 드러낸다.

- 모델: **YOLO11n**, 2,583,322 파라미터 · 6.4 GFLOPs · 입력 1×3×640×640, 6클래스.
- 데이터: 학습 데이터셋의 라벨이 export에서 누락돼 있었으나, **ultralytics 라벨 캐시에서
  복원**(train 2,388 / val 500, 클래스 균형)해 정확도 측정에 사용. (→ [복구 노트](#부록--데이터셋-복구))

## Method

```
best.pt ──ultralytics export──> OpenVINO FP32 IR
        └─ int8=True + NNCF PTQ (복원 데이터셋 캘리브레이션) ──> OpenVINO INT8 IR
정확도: 복원 val 500장으로 mAP(FP32 vs INT8)
지연:   난수 입력 N=100 · 맥 arm64 CPU / Intel CPU·iGPU·Arc B580
```
- 툴: ultralytics 8.4.135 · openvino 2026.3.1 · nncf 3.3.0.
- mAP는 합성(Houdini) val 기준 → 절대값보다 **FP32 대비 INT8 델타**가 유효한 지표.

## Results — 정확도 · 크기

| 구성 | 크기 | mAP50-95 | mAP50 |
|---|---|---|---|
| FP32 IR | 10.74 MB | 0.9302 | 0.9760 |
| **INT8 IR** | **3.39 MB (32%)** | **0.9255 (−0.46pp)** | 0.9770 (+0.10pp) |

→ **정확도 손실 없이 3.2배 경량화.**

## Results — 지연 (모델 단독, fps)

| 하드웨어 | FP32 | INT8 | INT8 배속 |
|---|---|---|---|
| 맥 arm64 CPU (M1 Pro) | 91.2 | 76.2 | **×0.84 (느려짐)** |
| Intel Core Ultra 5 225 | 44.8 | **104.0** | **×2.32** |
| Intel iGPU | 92.6 | 122.3 | ×1.32 |
| Intel Arc B580 (dGPU) | 847.7 | 853.0 | ×1.01 (포화) |

## Findings

1. **INT8 이득은 하드웨어에 종속된다.** 같은 INT8 모델이 맥 arm64 CPU에선 오히려 느리고
   (정수 가속 없음 → 에뮬레이션), **Intel CPU(VNNI)에선 2.3배 빨라진다.** "INT8=항상 빠름"은
   틀렸고, 타깃 하드웨어가 전제다.
2. **작은 모델은 강력한 dGPU에서 양자화의 속도 이점이 사라진다.** Arc B580은 FP32에서 이미
   848 fps로 연산이 병목이 아니라, INT8은 여기서 속도보다 **메모리·전력** 이점으로 봐야 한다.
3. **배포 전략 결론:** 저사양 Intel CPU 타깃이면 INT8이 결정적(2.3배 + 3.2배 경량).
   강력한 dGPU면 FP16로 충분.

## 정직한 한계

- val이 합성(Houdini)이라 mAP 절대값(0.93)은 분포 일치 효과가 크다. **실사 mAP는 별도 과제**
  (실사 라벨 필요) — [A2](soarm-robotarm-track.md) 계열로 확장.
- 지연은 **모델 단독**(전처리·NMS·게이트 제외). Hailo-8 INT8 76.5 fps(전체 파이프라인)와
  직접 비교하려면 같은 축 재측정 필요.
- FP16 CPU는 이 빌드에서 미가속(정상).

## 부록 — 데이터셋 복구

원본 YOLO export에 이미지·ultralytics 캐시만 있고 라벨 `.txt`가 누락돼 있었다. 캐시에 저장된
정규화 xywh 박스+클래스를 파싱해 train 2,388 / val 500 라벨을 복원(박스 7,181개, 6클래스 균형).
이 복원이 없었으면 INT8 정확도 축 자체가 불가능했다 — **데이터 엔지니어링이 실험을 성립시킨 사례.**

## 코드

`code/a1-edge-opt/` — `a1_bench_cpu.py`(맥 CPU 지연), `a1_bench_gpu_desktop.py`(Intel 3종 FP 지연),
`a1_int8_accuracy.py`(INT8 양자화 + mAP + 지연), `a1_bench_results.md`(전체 실측 로그).
