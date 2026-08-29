# Immortan — 자율주행 대회 🥇 1등

> **2026-06 ~ 2026-07 · 팀 6인 · Intel Physical AI 엔지니어 과정 내 대회**
>
> 코드: [`grippers-intel/Immortan-Project`](https://github.com/grippers-intel/Immortan-Project)
> (실제 주행에 쓰인 브랜치 `hease` · 제 작업 브랜치 `kica927/right`)
>
> **제 기여:** 전 브랜치 430커밋 중 **80건**. `kica927/right` 브랜치 114커밋,
> `hease` 대비 **+695 / −319줄**. 우회전 인식 · 검출 실패 방지 · LED 신호 · 속도.

---

## 1. Problem

MentorPi 메카넘 로봇으로 **정해진 코스를 자율주행**하며 미션을 수행한다.

| 미션 | 판단해야 하는 것 |
|---|---|
| 차선 추종 | 노란선이 화면 어디에 있는가 |
| 코너링 | 지금이 급커브인가 |
| 횡단보도 | 정지선인가, 오검출인가 |
| 신호등 | 빨강인가 초록인가, **얼마나 최근 정보인가** |
| 우회전 | 표지판이 진짜인가 |
| 주차 | 표지판까지 거리가 얼마인가 |

**대본으로 풀 수 없습니다.** 코스는 같아도 조명·주행선·검출 타이밍이 매번
다르므로, 매 프레임 관측하고 판단해야 합니다.

---

## 2. Architecture

```
카메라 (ascamera · RGB + Depth)
   ├──→ YOLOv5        표지판·신호등 박스
   │                  go · right · park · red · green · crosswalk
   └──→ 차선검출       LAB 색공간 → 노란선 중심 x
                ↓
          self_driving   판단 · 두뇌 (1,069줄)
                ↓
        /controller/cmd_vel        →  메카넘 4륜
        /ros_robot_controller/set_rgb  →  온보드 RGB LED
        GPIO 24·25·23·18           →  빵판 LED
```

| 방향 | 토픽 | 내용 |
|---|---|---|
| 구독 | `/ascamera/…/rgb0/image` | 컬러 영상 (차선검출) |
| 구독 | `/ascamera/…/depth0/image_raw` | 깊이(mm) — 주차 표지판 거리 |
| 구독 | `/yolov5_ros2/object_detect` | 검출 박스 |
| 구독 | `/odom` | 오도메트리 — 주차 정밀 이동 |
| 구독 | `/ros_robot_controller/button` | 출발/리셋 버튼 |
| 발행 | `/controller/cmd_vel` | `linear.x` · `linear.y` · `angular.z` |

---

## 3. My Contribution

| 영역 | 내용 |
|---|---|
| **우회전 미션** | 표지판 검출 후 90° 회전. 브랜치명이 `right angle` |
| **검출 실패 방지** | 커밋 `detect fail 방지` — 오검출·미검출 가드 |
| **LED 신호 체계** | 온보드 RGB + 빵판 LED (GPIO 4채널) |
| **속도 튜닝** | 커밋 `vel` — 순항/코너 속도 |
| 학습노트 작성 | 대회 후 전 기능을 재정리한 회고록 (38KB) |

---

## 4. Design Decisions

### 우선순위를 코드 구조에 박아 넣는다

```
image = 큐에서 프레임              (없으면 대기)
update_leds()                      ① LED 갱신
if parked: → 영구 정지
elif start:
    binary = get_binary(image)     ② LAB 로 노란색만
    ── 횡단보도/신호등 정지 ──      ③ 멈출지  ★ 최우선
    ── 주차 트리거 ──               ④
    lane_x = lane_detect(binary)   ⑤ 차선 중심
    ── 차선추종/코너/far 폴백 ──    ⑥
    mecanum_pub.publish(twist)     ⑦
```

**정지 판단(③)이 차선추종(⑥)보다 먼저입니다.** 멈춤 상태가 되면 아래 블록이
통째로 건너뛰어집니다. 즉 **"멈출 이유가 없을 때만 달린다"가 조건문이 아니라
구조로** 보장됩니다.

### 조향에는 near, 재획득에는 far

ROI 3개에서 **가까운 띠(near)** 와 **먼 띠 포함 최댓값(far)** 두 값을 냅니다.

- 조향은 **near** — far 를 쓰면 앞 코너를 미리 보고 **너무 일찍 꺾습니다**
- 차선을 잃으면 **far 폴백**

### 색공간은 RGB 가 아니라 LAB

밝기 변화에 RGB 보다 강해 **그림자가 져도** 노란선을 안정적으로 골라냅니다.

### 신호등에 "신선도"를 둔다

`red_hold_time = 1.5s`. 빨강을 본 지 얼마나 지났는지를 함께 봅니다 — 한 프레임
놓쳤다고 바로 출발하면 안 되고, 오래된 빨강으로 계속 서 있어도 안 됩니다.

### 횡단보도 오검출을 두 겹으로 거른다

`min_area = 1800` · `aspect = 2.0`. 면적과 종횡비 둘 다 통과해야 정지선으로
인정합니다.

---

## 5. Implementation

- **로봇** MentorPi Mecanum · **스택** ROS 2 · Python
- **비전** YOLOv5 (표지판·신호등) + LAB 차선검출
- 핵심 파일 `self_driving.py` (1,069줄) · `lane_detect.py` (233줄) ·
  `yolo_detect.py` (185줄)
- 워크스페이스 11패키지 (`app` · `driver` · `example` · `interfaces` ·
  `navigation` · `peripherals` · `slam` · `yolov5_ros2` …)

---

## 6. Problems & Debugging

**이 절이 이 프로젝트에서 가장 값진 부분입니다.**

### 6-1. 로봇이 "눈 감고" 횡단보도를 통과했다

```
Symptom      주행 중 횡단보도를 그냥 지나감
Measurement  로그의 프레임 공백 — 이미지가 일정 구간 아예 안 들어옴
Root Cause   카메라 USB 분리 (onCameraDetached) — 코드가 아닌 하드웨어
왜 계속 갔나  cmd_vel 을 안 보내면 로봇은 직전 명령을 유지한다
Fix          USB 케이블·전원 점검
```

> **`cmd_vel` 미발행은 정지가 아니라 "직전 명령 유지"입니다.** 입력이 끊긴
> 상태에서 마지막 전진 명령이 latch 되어 계속 달렸습니다.

### 6-2. "라인을 잃었다"가 사실은 "near 에서만 잃었다"였다

```
Symptom      차선 재획득 실패
Measurement  near=13, far=171     ← 두 값을 함께 로그에 남긴 것이 결정적
Root Cause   near ROI 에서만 놓쳤고 far 에는 선이 남아 있었다
Fix          far 폴백 — near 를 잃으면 far 기준으로 복귀
```

> **한 값이 아니라 여러 관점을 남긴 덕분에 해법이 보였습니다.**
> 하나만 찍었으면 "선을 잃었다"로 끝났을 것입니다.

### 6-3. 아무리 코드를 만져도 안 되는 것이 있었다

2번 코너에서 계속 오버슛했습니다. 파라미터를 바꿔도 개선되지 않았습니다.

**원인은 물리였습니다** — 제동거리와 검출 시점. 코너를 인식한 순간에는 이미
늦습니다.

> **교훈: 문제를 코드/물리로 먼저 분류한다.** 물리 한계를 코드로 고치려 하면
> 시간만 씁니다. 대응은 코드가 아니라 **`corner_speed = 0.25` 로 진입 속도를
> 낮추는 것**이었습니다.

### 6-4. 새 기능이 다른 상황을 망가뜨렸다

부작용이 대부분 여기서 났습니다. 그래서 **"언제 하면 안 되는지"를 기능과 함께
코딩**하게 됐습니다 — 코너 중 재획득 금지, 순간 누락 무시(디바운스).

---

## 7. Verification

- 대회 코스 실주행
- 매 프레임 `TURN?` · `crosswalk=` · `DRIVE lin=` 로그를 파일로 저장하고
  문제 구간의 값을 직접 읽어 원인 특정
- 두 변형(`self_driving_cross.py` · `self_driving_led.py`)으로 기능별 검증

---

## 8. Results

### 🥇 대회 1등

### 최종 파라미터 (실측)

| 영역 | 파라미터 | 값 |
|---|---|---|
| 차선추종 | `lane_setpoint` / `turn_threshold` | 130 / 200 |
| | `turn_angular_z` / `turn_recover_time` | −1.35 / 2.5 s |
| 재획득 | `far_setpoint` / `far_recover_gain` | 290 / 0.004 |
| 속도 | `normal_speed` / `corner_speed` | **0.45 / 0.25 m/s** |
| 횡단보도 | `crosswalk_stop_dist` / `duration` | 320 px / 1.0 s |
| | `min_area` / `aspect` | 1800 / 2.0 |
| 신호등 | `red_hold_time` / `red_min_area` | 1.5 s / 800 |
| 우회전 | `right_min_area` / `turn_right_duration` | 1000 / **3.3 s (≈90°)** |
| 주차 | `capture_dist` / `standoff` / `lateral` | 2.0 / 0.95 / 0.4 m |

### PID 튜닝에서 얻은 규칙

| 상황 | 대응 |
|---|---|
| 속도를 올리고 싶다 | **P ↑**(엑셀) · I 유지 또는 ↓ · **D ↑**(브레이크) |
| 차가 덜컹거린다 | **P ↓ · D ↑** |

---

## 9. Limitations

- 🔴 **2번 코너 오버슛** — 제동거리라는 물리 한계. 속도를 낮춰 회피했을 뿐
  근본 해결이 아닙니다
- 🔴 **카메라 USB 안정성** — 분리되면 감지 수단이 없습니다. 워치독이 없었습니다
- 🟡 **`park` 인식 실패** · **우회전 인식 실패**가 대회 직전까지 남아 있었습니다
- 🟡 좌측 차선 기준으로만 주행합니다 — 우측 기준 코스에는 그대로 못 씁니다
- 팀 프로젝트이고 실제 주행 코드는 `hease` 브랜치입니다. 제 기여는 위 3절 범위입니다

---

## 10. Future Work

이 프로젝트에서 겪은 것이 다음 두 곳으로 이어졌습니다.

| 여기서 | 다음에서 |
|---|---|
| `cmd_vel` 미발행 = 직전 명령 유지 | [grippers](grippers.md) — *"차량을 멈추려고 노드를 죽이지 않는다"* |
| 문제를 코드/물리로 분류 | grippers 데드밴드(0.05 m/s) · INSERT 오버슈트 |
| 로그로 원인을 특정 | grippers 제어 주기 1.6 → 9.6 Hz |
| 워치독이 없어 입력 단절을 못 잡음 | grippers `LinkWatchdog` · [RoboSec 불변식 I4](../plans/robosec/security_properties.md) |

**마지막 행이 특히 직접적입니다.** 여기서 카메라가 끊겨도 계속 달린 경험이,
grippers 에서 "링크 끊김과 정지 지시는 다른 사건이다"라는 설계로 이어졌습니다.
