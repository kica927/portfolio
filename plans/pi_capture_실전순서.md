# 실전 순서 — Pi 가 붙었을 때

> 로봇 앞에서 그대로 따라 치는 문서입니다.
> 왜 이렇게 만들었는지는 [`README.md`](README.md) 를 보세요.

**터미널을 3개 씁니다.** 미리 열어 두세요.

| | 어디 | 무엇 |
|---|---|---|
| **T1** | 맥 | 배포 · 수집 · 분석 |
| **T2** | Pi 컨테이너 | bag 녹화 |
| **T3** | Pi 컨테이너 | CSV 기록 (tap) |

---

# 0단계 — Pi 가 진짜 붙었는지 (맥, T1)

```
ping -c 2 raspberrypi.local
```

응답이 없으면 mDNS 가 안 잡히는 것이니 IP 로 갑니다. 과거 주소는
`10.82.133.189` 였고 DHCP 라 바뀝니다.

```
ssh pi@raspberrypi.local
```

들어가지면 바로 나옵니다 (`exit`). 접속만 확인한 것입니다.

---

# 1단계 — 배포 (맥, T1)

```
cd ~/Desktop/intel/grippers_project/pi_capture
./deploy.sh
```

IP 로 붙어야 하면:

```
PI=10.82.133.189 ./deploy.sh
```

**이렇게 나오면 성공입니다.**

```
대상: pi@raspberrypi.local · 컨테이너 IntelPi
1/3  Pi 홈으로 복사 (저장소 밖)
2/3  컨테이너 /tmp 로 복사
3/3  저장소가 그대로인지 확인
     OK — /grippers 변경 0건
```

**마지막 줄이 핵심입니다.** `변경 0건` 이 아니면 멈추고 원인을 보세요.

접속이 안 되면 아무것도 하지 않고 종료합니다.

---

# 2단계 — 컨테이너 들어가기 (T2)

```
ssh pi@raspberrypi.local
cd ~/docker && ./exec_shell.sh
```

**이 세션은 zsh 입니다.** `setup.bash` 가 아니라 `setup.zsh` 를 source 해야
합니다.

```
export ROS_DOMAIN_ID=21
source /opt/ros/humble/setup.zsh
source /ros2_ws/install/setup.zsh
source /home/ubuntu/third_party_ros2/third_party_ws/install/setup.zsh
```

확인:

```
echo $ROS_DOMAIN_ID
ros2 node list
```

`21` 이 나오고 노드 목록이 보여야 합니다.

---

# 3단계 — 환경 점검 (T2)

```
bash /tmp/pi_capture/preflight.sh
```

**아무것도 바꾸지 않습니다. 보기만 합니다.**

기대하는 출력:

```
=== 1. ROS 환경 ===
   OK  ROS_DOMAIN_ID=21
   OK  ros2 있음

=== 2. 살아 있는 노드 (죽이지 않습니다, 보기만) ===
       /mission_orchestrator
       /base_driver
       /perception_node
   OK  perception 계열 살아 있음

=== 3. 관측할 토픽 ===
   OK  /cmd_vel (average rate: 9.612)
   OK  /odom_raw (average rate: 30.1)
   OK  /mission/state
   ?? /scan 없음

=== 4. 디스크 여유 ===
   OK  /tmp 여유 42 GB

=== 5. 저장소를 건드리지 않았는지 ===
   OK  /grippers 작업트리 깨끗 (변경 0건)

판정: 수집 가능
```

## 여기서 봐야 할 것 두 가지

**`/cmd_vel` 의 average rate.** 9.6 근처면 정상입니다. **1.6 이 나오면**
제어 주기 문제가 재발한 것이니 수집 전에 그것부터 보셔야 합니다.

**`perception` 이 안 보이면** 재기동이 필요합니다 — 배포·재시작 뒤에는 항상
그렇습니다. `depth_cam_rotate_node` 도 같이 확인하세요.

---

# 4단계 — 30초 시험 (T3) ★ 첫날 반드시

**`tap.py` 는 실기에서 한 번도 안 돌아 봤습니다.** 본 수집 전에 짧게 확인합니다.

새 SSH 세션을 열어 컨테이너로 들어간 뒤 (2단계 반복), 30초만:

```
python3 /tmp/pi_capture/tap.py --out /tmp/capture_out/smoke --max-seconds 30
```

**시작할 때 이런 줄들이 나와야 합니다.**

```
[INFO] 구독 /cmd_vel  [geometry_msgs/msg/Twist]
[INFO] 구독 /odom_raw  [nav_msgs/msg/Odometry]
[INFO] 구독 /mission/state  [std_msgs/msg/String]

기록 중 — /tmp/capture_out/smoke
Ctrl+C 로 종료합니다.
```

30초 뒤 요약:

```
=== 기록 요약 ===
       288  /cmd_vel
       901  /odom_raw
         3  /mission/state
  --------
      1192  합계 · 30.0초
```

파일 확인:

```
ls -la /tmp/capture_out/smoke
head -3 /tmp/capture_out/smoke/cmd_vel.csv
```

**CSV 에 헤더와 숫자가 보이면 성공입니다.**

## 시험이 실패하면

| 증상 | 뜻 | 대응 |
|---|---|---|
| `구독할 토픽이 없습니다` | 자동 탐색 실패 | 출력에 찍힌 토픽 목록을 보고 `--topics /cmd_vel /odom_raw ...` 로 직접 지정 |
| 특정 토픽만 0행 | QoS 불일치 또는 발행 없음 | `ros2 topic hz <토픽>` 으로 발행 자체를 먼저 확인 |
| `타입 로드 실패` | 커스텀 메시지 | 그 토픽은 bag 으로만 남기고 CSV 는 포기 |
| `ROS_DOMAIN_ID 가 21 이 아닙니다` | export 누락 | 2단계 다시 |

> ⚠️ **`assert 퍼블리셔가 생겼습니다` 가 나오면 즉시 알려 주세요.** 있어서는
> 안 되는 일이고, 그대로 쓰면 안 됩니다.

---

# 5단계 — 본 수집 (T2 + T3)

**녹화를 먼저 켜고, 그다음 미션을 시작합니다.** 순서가 반대면 시작 구간을
놓칩니다.

## T2 — bag 녹화

```
export ROS_DOMAIN_ID=21
bash /tmp/pi_capture/record.sh "통주행 성공 1회차"
```

## T3 — CSV 기록

```
export ROS_DOMAIN_ID=21
python3 /tmp/pi_capture/tap.py --out /tmp/capture_out/run_$(date +%H%M%S) --label "통주행 성공 1회차" --max-seconds 900
```

## 그다음 평소대로 미션을 돌립니다

**수집 도구는 아무것도 지시하지 않습니다.** 평소 하시던 대로 진행하세요.

시행이 끝나면 **T3 먼저** Ctrl+C, 그다음 T2 Ctrl+C.

> **왜 둘 다 켜나:** bag 은 나중에 무엇이든 다시 꺼낼 수 있는 원본이고, CSV 는
> 맥에서 ROS 없이 바로 분석되는 형태입니다. bag 만 있으면 맥에서 못 읽고,
> CSV 만 있으면 나중에 다른 토픽이 필요할 때 되돌릴 수 없습니다.

## 끝나면 바로 INDEX 채우기

```
vi /tmp/capture_out/INDEX.md
```

`(채울 것)` 자리에 결과를 적습니다.

```
| `run_20260902_143012` | 09-02 14:30 | 통주행 성공 1회차 | DONE 도달 | rook 파지 1회 실패 후 재시도 성공 |
```

**3개월 뒤에는 bag 이름만 보고 무엇이었는지 기억나지 않습니다.**

---

# 6단계 — 무엇을 몇 번 돌릴 것인가

`plans/2026-09-08-capture.md` 의 P1 목록입니다.

```
[ ] 통주행 성공          3회 이상
[ ] 파지 실패 → 재시도    2회 이상
[ ] INSERT 성공          클래스별 1회 (6클래스)
[ ] INSERT 차단(⛔)      1회
[ ] 사선 진입            15°·30° 각 3회
```

**정지 이벤트는 따로 만들 필요가 없습니다.** GRASP 는 베이스 정지를 요구하고
INSERT 접근은 정지로 끝나므로, 통주행 한 번에 정지가 여러 번 들어갑니다.
`analyze_stop.py` 가 그것을 찾아냅니다.

**워치독만 예외입니다** — 정상 운행에는 링크 침묵이 없습니다. 분석기가
"주행 중 침묵이 없었습니다" 라고 하면, 그때 Host 를 의도적으로 끊는 시행이
따로 필요합니다.

---

# 7단계 — 맥으로 가져오기 (T1)

시행 몇 개가 쌓이면:

```
cd ~/Desktop/intel/grippers_project/pi_capture
./collect.sh
```

```
수집 → /Users/lemma/Desktop/intel/grippers_recordings_final
1/2  컨테이너 → Pi 홈
     3.2G    /home/pi/capture_out
2/2  Pi → 맥
```

> **하루에 한 번은 돌리세요.** Pi 의 `/tmp` 는 컨테이너를 다시 만들면
> 사라집니다. **9월 7일에 한 번 더** 최종본을 가져오세요.

---

# 8단계 — 분석 (맥, T1)

```
cd ~/Desktop/intel/grippers_project/pi_capture
python3 mac/analyze_stop.py --dir ~/Desktop/intel/grippers_recordings_final/run_143012
```

```
정지 이벤트 7건

  #   T_stop(ms)   coast(ms)   overshoot(mm)  비고
------------------------------------------------------------
  1        104.2       612.0            18.3
  2        104.2       598.0            17.9
  ...
  7       1240.0       610.0            18.1  링크 결측 — 제외

=== 요약 ===
        T_stop  n=6   중앙값 104.2ms  범위 104.2~208.3ms
          오버슈트  n=6   중앙값 18.1mm

허용창 ±15 mm 와 비교:
  창을 넘은 정지 6/6건
  ⛔ 중앙값이 허용창보다 큽니다 — 오버슈트가 제어되지 않습니다
```

**이 마지막 세 줄이 RoboSec 리포트의 결과 하나입니다.**
`T_stop` 의 실측값이 여기서 처음 나옵니다 — 지금 문서에 있는 235 ms 는
계산값(Host 125 + UDP 10 + Pi 100)이지 잰 값이 아닙니다.

```
python3 mac/analyze_watchdog.py --dir ~/Desktop/intel/grippers_recordings_final/run_143012
```

```
cmd_vel 8210행 · 추정 발행 주기 9.61 Hz
설계 기준 3사이클 @ 9.6 Hz = 312 ms 예상

침묵 구간 0건 (그중 주행 중이던 것 0건)
주행 중 침묵이 없었습니다.
→ 정상 운행 로그만으로는 워치독이 안 잡힙니다.
```

이 메시지가 나오면 **P2-2 시행이 따로 필요하다**는 뜻입니다.

---

# 9단계 — 숫자를 옮겨 적기

측정값이 나오면 세 곳에 반영합니다.

| 어디 | 무엇 |
|---|---|
| `portfolio/plans/robosec/security_properties.md` | I2 의 `T_stop`, I4 의 워치독 시간 |
| `portfolio/projects/grippers.md` §8 | 실측 표에 추가 |
| grippers 저장소 `baseline_constants.py` | 상수 갱신 (**팀 절차대로 브랜치·PR**) |

**세 번째는 팀 저장소를 바꾸는 일이라 별개입니다.** 수집 도구는 여기 관여하지
않습니다.

---

# 하루가 잘 끝났을 때의 모습

```
[ ] preflight 판정: 수집 가능
[ ] 시행 3~5개, bag + CSV 짝으로
[ ] INDEX.md 의 결과 칸이 전부 채워짐
[ ] collect.sh 로 맥에 복사됨
[ ] analyze_stop.py 가 정지 이벤트를 찾아냄
[ ] /grippers 변경 0건        ← 매번 확인
```

마지막 줄을 매번 확인하세요.

```
docker exec IntelPi bash -lc 'cd /grippers && git status --porcelain | wc -l'
```

`0` 이 아니면 수집 도구가 아니라 다른 원인이겠지만, 어느 쪽이든 알아야 합니다.

---

# 문제가 생기면

| 증상 | 대응 |
|---|---|
| `deploy.sh` 접속 실패 | 아무것도 안 바뀌었습니다. IP 로 재시도 |
| `preflight` 에서 `/cmd_vel` 1.6 Hz | 제어 주기 문제 재발. 수집보다 이게 먼저 |
| `perception` 안 보임 | 재기동 필요 (배포·재시작 뒤에는 항상) |
| 디스크 부족 | `collect.sh` 로 옮기고 `/tmp/capture_out` 정리 |
| tap 이 토픽을 못 찾음 | `--topics` 로 직접 지정 |
| bag 이 너무 큼 | 영상은 이미 제외돼 있습니다. 시행을 짧게 |

## 절대 하지 않을 것

- **차량을 멈추려고 노드를 죽이지 않습니다** — 마지막 명령이 latch 된 채
  남습니다. 정지는 정상 경로로
- 캘리브레이션 파일(`host/calib/*.npz`)을 옮기거나 지우지 않습니다
- `/grippers` 안에 수집 결과를 쓰지 않습니다
