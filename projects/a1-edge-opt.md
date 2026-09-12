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
| Intel NPU (Core Ultra 5 225 내장, f16 고정) | 136.2 | **123.2** | **×0.90 (느려짐)** |

## Findings

1. **INT8 이득은 하드웨어에 종속된다.** 같은 INT8 모델이 맥 arm64 CPU에선 오히려 느리고
   (정수 가속 없음 → 에뮬레이션), **Intel CPU(VNNI)에선 2.3배 빨라진다.** "INT8=항상 빠름"은
   틀렸고, 타깃 하드웨어가 전제다.
2. **작은 모델은 강력한 dGPU에서 양자화의 속도 이점이 사라진다.** Arc B580은 FP32에서 이미
   848 fps로 연산이 병목이 아니라, INT8은 여기서 속도보다 **메모리·전력** 이점으로 봐야 한다.
3. **배포 전략 결론:** 저사양 Intel CPU 타깃이면 INT8이 결정적(2.3배 + 3.2배 경량).
   강력한 dGPU면 FP16로 충분.
4. **"엣지 AI 가속기 = 곧바로 쓸 수 있다"는 것도 오해다.** Core Ultra 5 225는 NPU를
   내장하고 커널 드라이버(`intel_vpu`)도 정상 로드되지만, OpenVINO는 처음엔 `NPU`를
   `available_devices`에 올리지 못했다. 조사 결과 커널·권한·OpenVINO 파이썬 패키지(NPU
   플러그인 `.so` 포함)는 전부 정상이고, 딱 하나 — **NPU 전용 level-zero 컴파일러
   (`libopenvino_intel_npu_compiler_loader.so`)만 시스템에 없었다.** 이 컴파일러는 PyPI가
   아니라 Intel의 `.deb` 패키지(`intel-driver-compiler-npu`)로만 배포된다(직접
   `pip download`로 부재를 확인). GPU 스택은 동등한 `libze_intel_gpu.so`가 이미 있어
   `GPU.0`/`GPU.1`은 문제없이 잡히는 것과 대조적이다. **NPU/GPU/CPU는 같은 OpenVINO API로
   추상화돼 있어도, 실제로는 각 벤더 드라이버 계층이 별도로 완비돼야 한다** — "플러그인이
   있다"와 "구동된다" 사이의 간극을 실측으로 확인했다. 이후 Intel 공식 GitHub 릴리즈에서
   `.deb` 3종(`intel-driver-compiler-npu`·`intel-fw-npu`·`intel-level-zero-npu`)을 받아
   설치하니 즉시 인식됐다 — 원인 진단이 정확했다는 뜻이다.
5. **NPU는 GPU/CPU와 다른 종류의 가속기다.** 정밀도 힌트로 FP32를 주면 파싱 에러로
   거부한다 — NPU는 힌트로 고르는 게 아니라 **애초에 FP16 고정 아키텍처**다. 그리고
   **INT8 IR을 NPU에 올리면 오히려 느려진다**(136.2→123.2 fps, −9.6%) — NPU가 INT8
   텐서를 결국 FP16으로 되돌려 처리하면서 양자화 그래프의 dequantize 오버헤드만 얹기
   때문으로 보인다. Arc B580(포화라 무의미)에 이어 **NPU도 "INT8=항상 빠름"의 반례**다.
   NPU의 절대 성능(136 fps)은 CPU(91 fps)보다는 빠르지만 iGPU와 비슷한 수준이고
   Arc B580(849 fps)에는 크게 못 미친다 — 이 데스크탑 구성에서 NPU의 존재 의의는
   "속도"보다 **낮은 전력으로 상시 가동**하는 쪽에 가깝다(전력 측정은 이번 범위 밖).

## 정직한 한계

- val이 합성(Houdini)이라 mAP 절대값(0.93)은 분포 일치 효과가 크다. **실사 mAP는 별도 과제**
  (실사 라벨 필요) — [A2](soarm-robotarm-track.md) 계열로 확장.
- 지연은 **모델 단독**(전처리·NMS·게이트 제외). Hailo-8 INT8 76.5 fps(전체 파이프라인)와
  직접 비교하려면 같은 축 재측정 필요.
- FP16 CPU는 이 빌드에서 미가속(정상).
- **NPU 측정은 2026-09-12에 완료됐다**(사용자 승인 하에 Intel 공식 드라이버 설치, 상세는
  [실측 로그](code/a1-edge-opt/a1_bench_results.md) 참고). 다만 같은 실행에서 CPU 수치가
  기존 확정치(44.8/104.0 fps)와 약 2배 차이(90.8/207.6 fps)가 났고, **그 원인(스레드
  설정·전력 프로파일 차이 등)은 특정하지 않았다.** CPU 확정치는 2026-08-31 값을 그대로
  유지하고, NPU 수치는 이 편차와 무관하게 독립적으로 신뢰한다(NPU는 이번에 처음 측정된
  값이라 비교 대상 자체가 없다).
- NPU 절대 성능(136 fps)과 iGPU/Arc의 격차는 확인했지만, **전력 소비는 어느 디바이스도
  측정하지 않았다.** "NPU는 저전력 상시 가동에 유리하다"는 Findings의 해석은 아키텍처
  특성에 근거한 추정이며 실측이 아니다.

## 부록 — 데이터셋 복구

원본 YOLO export에 이미지·ultralytics 캐시만 있고 라벨 `.txt`가 누락돼 있었다. 캐시에 저장된
정규화 xywh 박스+클래스를 파싱해 train 2,388 / val 500 라벨을 복원(박스 7,181개, 6클래스 균형).
이 복원이 없었으면 INT8 정확도 축 자체가 불가능했다 — **데이터 엔지니어링이 실험을 성립시킨 사례.**

## 코드

`code/a1-edge-opt/` — `a1_bench_cpu.py`(맥 CPU 지연), `a1_bench_gpu_desktop.py`(Intel CPU·iGPU·
Arc B580·NPU 지연, NPU 포함 4-way 측정 완료),
`a1_int8_accuracy.py`(INT8 양자화 + mAP + 지연), `a1_bench_results.md`(전체 실측 로그,
NPU 드라이버 설치·측정 과정 포함).
