# grippers-host-mac — Windows 전용 Host 스택의 Apple Silicon 이식

> **2026-08 · 단독 작업**
>
> 코드: [`kica927/grippers-host-mac`](https://github.com/kica927/grippers-host-mac)
>
> 저장소의 `README.md` 는 **이식 작업의 기술 기록**입니다 — 무엇을 어떻게
> 고쳤는지가 거기 있습니다. 이 문서는 그 앞뒤 — **왜 했는가 · 무엇을 얻었는가 ·
> 무엇을 배웠는가** — 를 다룹니다.

---

## Problem — 왜 이식이 필요했나

`grippers` 팀의 Host PC 코드는 **Windows 전용**이었습니다. `cv2.VideoCapture` 를
여덟 군데에서 `CAP_DSHOW` 로 직접 부르고, 카메라 이름은 DirectShow COM
인터페이스를 `ctypes` 로 호출해 읽었습니다.

제 개발 장비는 Apple Silicon 맥이고, Host 코드를 돌릴 Windows 장비는 팀 안에
한 대뿐이었습니다. **로봇 1대를 5명이 나눠 쓰는 병목 위에 Host 1대 병목이
겹쳐 있는 상태**였습니다.

문제는 그 위험이 조용하다는 것입니다. macOS 에도 `cv2.CAP_DSHOW` 상수는 있고(700)
예외도 안 납니다 — `isOpened()` 가 False 를 돌려줄 뿐이라 **카메라가 없는 것과
구별이 안 됩니다.**

착수 시점의 미지수는 **OpenVINO 와 geti-sdk 가 Apple Silicon 을 지원하는가**
였습니다. 여기서 막히면 이식 자체가 성립하지 않습니다.

---

## My Contribution

| | 내용 |
|---|---|
| **플랫폼 분기 통합** | `host/camera_backend.py` (신규) — 여덟 군데 흩어진 백엔드 선택을 한 곳으로. Windows 동작은 불변 |
| **장치 열거 교체** | `host/aruco/camera_devices.py` — DirectShow COM → `system_profiler`. 공개 API 4종은 그대로 두고 가장 아래 한 층만 교체 |
| **실패를 소리 나게** | `lock_focus()` 가 미지원을 조용히 넘기지 않고 경고를 반환, 호출부가 stderr 에 한 번 출력 |
| **사본 동기화 검사** | `tools/check_domain_sync.py` — `domain/` 사본이 조용히 낡는 것을 종료 코드로 차단 |
| **실기 검증** | C920 두 대 · 실제 추론 · FSM 전이 · 루프 주파수 측정 |
| **화면 배치** | `--display` / `--cam-width` / `LIVEMAP_SIZE_IN` — 다중 모니터에서 창이 겹치지 않게 |

---

## Results — 측정값

**막힐 줄 알았던 지점이 실제로는 문제가 아니었습니다.**

| | 추론 1회 | 루프 |
|---|---|---|
| Host 팀 Windows CPU | 364 ms | 7.0 Hz (143 ms) |
| Host 팀 Windows iGPU | 250 ms | — |
| **Apple M1 Pro (CPU)** | **130 ms (7.7 Hz)** | **9.6~10.1 Hz (99~104 ms)** |

Host 팀은 검출 불일치 때문에 iGPU 를 버리고 CPU 로 확정했는데, **M1 Pro 의 CPU 가
그 iGPU 보다도 빠르므로 디바이스 선택 문제 자체가 사라집니다.**

렌더 비중도 달라졌습니다 — Windows 는 143 ms 중 90 ms 가 화면이었는데 여기서는
99 ms 중 21 ms 입니다.

검출 결과도 배관만 도는 것이 아니라 제대로 나옵니다:

```
_annotated.jpg   star:0.86
00001.jpg        star:0.87, rook:0.83, soccer:0.79
00002.jpg        star:0.84, rook:0.81, soccer:0.79
```

---

## What Failed — 내 첫 판단이 틀렸다

이식 과정에서 **제가 내린 결론이 실기에서 정반대로 뒤집힌 사례**가 있습니다.

열거 결과는 이렇게 나왔습니다:

```
AVFoundation / system_profiler :  [0] FaceTime  [1] C920  [2] C920
```

그래서 "원본의 `CAM_INDICES = (0, 1)` 은 내장 카메라를 잡는 틀린 값이고, 이름으로
골라야 한다" 고 적고 그렇게 구현했습니다. **실제로 열어 보니 반대였습니다:**

```
실제 cv2.VideoCapture           :  [0] C920  [1] C920  [2] FaceTime
```

OpenCV 는 외장을 먼저 놓습니다. 원본의 `(0, 1)` 이 이 맥에서도 맞는 값이었고,
제 "이름 기반" 코드가 `[1, 2]`(C920 한 대 + 내장 카메라)를 골라 **오른쪽 화면에
사람 얼굴이 나왔습니다.**

`AVCaptureDeviceDiscoverySession` 에 외장 타입을 먼저 요구해도 macOS 가 제
순서대로 돌려주므로, **열거 결과로는 cv2 인덱스를 복원할 수 없습니다.** 그래서
`list_video_devices()` 는 macOS 에서 빈 목록을 돌려주고 호출부가
`config.CAM_INDICES` 로 떨어지게 되돌렸습니다.

인덱스를 확정하는 유일하게 확실한 방법은 **찍어 보는 것**입니다.

---

## Lessons Learned

1. **조용한 실패가 시끄러운 실패보다 비쌉니다.** `CAP_DSHOW` 도, TCC 카메라 권한
   거부도, 지원되지 않는 `cap.set()` 도 전부 예외를 안 던집니다. 이식에서 시간을
   가장 많이 먹은 것은 코드를 고치는 일이 아니라 **무엇이 실패했는지 알아내는
   일**이었습니다. 그래서 새로 쓴 코드는 미지원을 반환값으로 알립니다.
2. **열거와 인덱스는 다른 것입니다.** 플랫폼이 이름을 알려준다고 해서 그 순서가
   라이브러리의 인덱스라는 보장은 없습니다. Windows 에서는 우연히 같았을 뿐입니다.
3. **문서에서 규격을 베끼지 않는 파일은 이식에서 손댈 것이 없습니다.**
   `vehicle_link.py` 는 `domain/` 을 직접 import 해서 한 줄도 안 고쳤습니다.
   그 덕에 저장소 레이아웃(`repo/host/`, `repo/domain/`)을 원본과 같이 유지했습니다.
4. **사본은 반드시 낡습니다.** 본 저장소가 사본 문제로 세 번 당한 뒤, 사람의
   주의력이 아니라 **종료 코드**로 막기로 했습니다.

---

## Limitations

- **초점 고정 불가** — AVFoundation 백엔드가 `CAP_PROP_AUTOFOCUS`/`CAP_PROP_FOCUS`
  를 지원하지 않습니다. C920 은 초점이 움직이면 초점거리가 같이 변해서 캘리브레이션한
  내부 파라미터가 그 순간부터 틀린 값이 됩니다. **ArUco 위치 정확도가 Windows 만큼
  안 나올 수 있습니다.** 회피책은 카메라 쪽에 있습니다 — UVC 명령으로 미리 고정하면
  OpenCV 가 안 건드립니다.
- **`model.bin` 미포함** — 가중치 85MB 를 LFS 로 올릴지 별도 배포로 뺄지 원본
  저장소가 아직 정하지 않아, 그 결정을 앞질러 가지 않으려고 ignore 합니다.
- **실기 통합 미완** — `--mock-complete` 로 차량 없이 FSM 전이까지만 확인했습니다.
