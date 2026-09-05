# pi_capture — 로봇 마지막 10일 수집 도구

> 2026-09-08 하드웨어 종료 전에 확보해야 할 값을 재기 위한 스크립트 모음입니다.
> 계획 전문 → 포트폴리오 저장소 `plans/2026-09-08-capture.md`

---

# 🔒 진행 중인 프로젝트에 영향을 주지 않는다 — 어떻게 보장했나

이것이 이 도구의 최우선 설계 조건이었습니다. 네 가지로 보장합니다.

## 1. `/cmd_vel` 에 발행하지 않습니다

팀 README 의 제약입니다:

> **`/cmd_vel` 발행 주체는 언제나 `base_driver` 하나뿐입니다. 둘이 되면 명령이
> 경합해 로봇이 떨리거나 타이밍에 따라만 재현되는 버그가 납니다.**

`tap.py` 는 **구독만 합니다.** 퍼블리셔·서비스 서버·액션 서버를 하나도 만들지
않고, 서비스를 호출하지도 않습니다. 마지막 방어선으로 시작 시점과 종료 시점에
`assert len(node.publishers) == 0` 을 검사합니다 — 퍼블리셔가 생기면 즉시
중단됩니다.

부하는 `ros2 bag record` 와 같은 종류(구독자 하나 추가)입니다. 그건 이미 팀의
표준 관행입니다.

## 2. 저장소에 아무것도 쓰지 않습니다

- 스크립트는 컨테이너 자체 파일시스템의 `/tmp/pi_capture` 로 들어갑니다.
  공유 마운트(`~/docker/shared/grippers` = `/grippers`)를 쓰지 않습니다
- 출력은 `/tmp/capture_out` 입니다
- `tap.py` 와 `record.sh` 는 출력 경로에 `/grippers` 가 있으면 **거부하고
  종료**합니다
- `deploy.sh` 는 배포 직후 `git status --porcelain | wc -l` 로 저장소가
  그대로인지 확인해 보고합니다

> `recordings/` 는 `.gitignore` 에 없어서, 거기에 쓰면 `git status` 가
> 더러워집니다. 그래서 쓰지 않습니다.

## 3. 노드를 죽이거나 재시작하지 않습니다

`preflight.sh` 는 `ros2 node list` 로 **보기만** 합니다. `pkill` 도
`ros2 lifecycle` 도 쓰지 않습니다. 파라미터도 바꾸지 않습니다.

## 4. 능동 실험(명령 주입) 스크립트는 만들지 않았습니다

`T_stop` 을 재려고 차량에 직접 명령을 넣는 스크립트는 **의도적으로 넣지
않았습니다.** 대신 **정상 운행 중에 자연히 발생하는 정지**를 로그에서 찾아
같은 값을 계산합니다.

이유는 두 가지입니다.

- 명령을 넣는 순간 "영향 없음" 이 깨집니다
- **필요가 없습니다.** GRASP 는 베이스 정지를 요구하고 INSERT 접근은 정지로
  끝나므로, 정상 미션 한 번에 정지 이벤트가 여러 개 생깁니다

정말로 통제된 주입이 필요해지면 그때 따로 만들면 됩니다.
**그 판단은 사용자가 합니다.**

---

# 구성

```
pi_capture/
├── deploy.sh              맥 → Pi 컨테이너 /tmp (저장소 안 건드림)
├── collect.sh             Pi → 맥 (읽기만)
├── pi/                    Pi 컨테이너에서 실행
│   ├── preflight.sh       환경 점검 — 읽기 전용
│   ├── record.sh          ros2 bag 녹화 래퍼 + INDEX 자동 기록
│   └── tap.py             수동 CSV 기록기 — 구독만
└── mac/                   맥에서 실행 (Pi 불필요)
    ├── analyze_stop.py       T_stop · 오버슈트  → 불변식 I2
    └── analyze_watchdog.py   워치독 반응 · 표류 → 불변식 I4
```

---

# 쓰는 순서

## Pi 가 살아나면

```
cd ~/Desktop/intel/pi_capture
./deploy.sh
```

접속이 안 되면 아무것도 안 하고 종료합니다.

컨테이너 안에서 (`cd ~/docker && ./exec_shell.sh`):

```
export ROS_DOMAIN_ID=21
bash /tmp/pi_capture/preflight.sh
```

`판정: 수집 가능` 이 나오면 다음으로.

## 시행마다 — 두 개를 같이 켭니다

**터미널 1 — bag 녹화:**

```
export ROS_DOMAIN_ID=21
bash /tmp/pi_capture/record.sh "통주행 성공 1회차"
```

**터미널 2 — CSV 기록:**

```
export ROS_DOMAIN_ID=21
python3 /tmp/pi_capture/tap.py --out /tmp/capture_out/run_$(date +%H%M%S) \
  --label "통주행 성공 1회차" --max-seconds 900
```

> **둘 다 켜는 이유:** bag 은 나중에 무엇이든 다시 꺼낼 수 있는 원본이고,
> CSV 는 맥에서 ROS 없이 바로 분석할 수 있는 형태입니다. bag 만 있으면 맥에서
> 못 읽고, CSV 만 있으면 나중에 다른 토픽이 필요할 때 되돌릴 수 없습니다.

시행이 끝나면 **INDEX.md 의 '결과' 칸을 바로 채우세요.**

## 맥으로 가져와 분석

```
cd ~/Desktop/intel/pi_capture
./collect.sh
python3 mac/analyze_stop.py --dir ~/Desktop/intel/grippers_recordings_final/run_XXXX
python3 mac/analyze_watchdog.py --dir ~/Desktop/intel/grippers_recordings_final/run_XXXX
```

---

# 분석기가 내는 값

## analyze_stop.py → 불변식 I2

```
        T_stop  n=5   중앙값 104.2ms  평균 104.2ms  범위 104.2~104.2ms
      관성 주행 시간  n=5   중앙값 625.0ms
          오버슈트  n=5   중앙값 7.1mm

허용창 ±15 mm 와 비교:
  창을 넘은 정지 0/5건
  ✅ 중앙값이 허용창 안입니다
```

**지금 문서에 있는 235 ms 는 계산값(Host 125 + UDP 10 + Pi 100)이지 실측이
아닙니다.** 이 스크립트가 그 자리를 채웁니다.

발행이 오래 끊긴 구간은 **"링크 결측 — 제외"** 로 표시하고 요약에서 뺍니다.
섞으면 중앙값이 오염되기 때문입니다.

## analyze_watchdog.py → 불변식 I4

```
cmd_vel 190행 · 추정 발행 주기 9.60 Hz
설계 기준 3사이클 @ 9.6 Hz = 312 ms 예상
실측 주기 기준 예상    = 313 ms
```

제어 주기가 1.6 Hz 였을 때 "3사이클" 은 0.3초가 아니라 **1.8초** 였습니다.
9.6 Hz 로 고친 뒤의 실제 값은 아직 아무도 재지 않았습니다.

정상 운행 로그에 주행 중 침묵이 없으면 그렇게 말해 줍니다 — 그 경우에만
Host 를 의도적으로 끊는 시행이 필요합니다.

---

# 검증

두 분석기는 **진값을 아는 합성 로그로 시험했습니다.**

| 주입한 값 | 복원한 값 |
|---|---|
| 정지 지연 1사이클 @ 9.6 Hz = 104.2 ms | **104.2 ms** |
| 발행 주기 9.6 Hz | **9.60 Hz** |
| 침묵 1.0초 1건 | **1건, 정지 이벤트와 분리됨** |

`tap.py` 는 **실기가 없어 아직 실행해 보지 못했습니다.** 문법 검사만 통과한
상태이므로, Pi 가 살아나면 `preflight.sh` → 짧은 `tap.py`(예: `--max-seconds 30`)
로 **먼저 시험 삼아 한 번** 돌려 CSV 가 제대로 나오는지 확인하세요.

---

# 안 하는 것

- 차량에 명령을 넣지 않습니다
- 노드를 죽이거나 재시작하지 않습니다
- 저장소·캘리브레이션 파일(`host/calib/*.npz`)을 건드리지 않습니다
- `colcon build` 를 하지 않습니다 (워크스페이스 불변)
- 파라미터를 바꾸지 않습니다
