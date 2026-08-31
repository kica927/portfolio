# robot-link-timing — 분산 로봇 링크 타이밍 특성화

> grippers/Immortan 의 실제 통신 경로 **UDP(Host↔Pi)** 와 **시리얼(Pi↔STM32)** 의
> 지연·지터·클럭오프셋·손실·재정렬을 계측한다. "증상이 아니라 계측" — 2023 5G/UDP,
> 2026 RoboSec 로 이어온 통신 축을 **측정 데이터**로 잇는다.
>
> 하드웨어 종료(2026-09-08) 전에 **로그만** 확보하면, 분석·시각화는 전부 오프라인.

## 토폴로지

```
[Host = 맥]  --UDP-->  [Pi]  --Serial-->  [STM32]   (로봇 저수준 보드)
     udp_probe(prober)   udp_probe(responder)   실제 프로토콜 계측(passive)

참고 기준선:  [Host] --USB-Serial--> [Arduino Uno echo]   (로봇 밖 통제 기준값)
                         serial_probe
```

## 도구

| 파일 | 역할 |
|---|---|
| `udp_probe.py` | UDP 왕복·**편도·클럭오프셋**(NTP식 4-타임스탬프)·지터·손실·재정렬 |
| `serial_probe.py` + `arduino/serial_echo/` | 시리얼 왕복·지터·손실 (Arduino echo) |

측정 정의: RTT = `(T3-T0)-(T2-T1)`(응답 처리시간 제외), offset = `((T1-T0)+(T2-T3))/2`,
지터 = 평균 `|ΔRTT|`(RFC3550 근사).

## 실행

### UDP (검증 완료 — 루프백 500/500, RTT mean 0.265 ms)
```
# 응답측(Pi)      python udp_probe.py responder --port 6000
# 송신측(맥)      python udp_probe.py prober --target <PI_IP> --port 6000 --rate 200 --count 2000 --out udp_idle.jsonl
```

### 시리얼 기준선 (Host↔Arduino Uno echo — 로봇 밖 통제 기준값)
Uno echo 는 펌웨어 처리시간이 최소라 **USB-serial 링크 자체의 하한**을 준다.
```
pip install pyserial
python serial_probe.py --port /dev/cu.usbserial-XXX --rate 200 --count 2000 --out serial_ref.jsonl
```
**검증 결과(맥↔Uno):** 1000/1000, 왕복 mean 7.08 ms, p95 8.3, 지터 0.014 ms.

### 실기 시리얼 (Pi↔STM32) — echo 아님, 실제 프로토콜 계측
STM32 는 grippers 펌웨어(모터·부저 등)를 돌리지 실험용 echo 를 하지 않는다. 따라서
**기존 Pi↔STM32 프로토콜의 명령→응답 왕복을 그대로 타임스탬프**해 잰다(passive/instrumented).
이 값은 Uno echo 기준선보다 **펌웨어 처리시간만큼 크다** — 그 차이가 곧 STM32 쪽 처리비용이다.

## 캡처 프로토콜 (9/8 전, 부하 스윕)

각 링크를 **idle · 중간(perception 동작) · 고부하(perception+모터+주행)** 3단계로
각 1~2분. UDP 는 Pi 에서 responder, 맥에서 prober. 시리얼(Pi↔STM32)은 기존 프로토콜
교환을 계측. Uno echo 기준선(맥/데스크탑)은 로봇과 무관하게 이미 확보.

시행마다 `INDEX.md` 한 줄: 파일명 · 링크 · 부하단계 · 특이.

## 이후 (오프라인)

지연 분포·지터·손실률의 부하 의존성, 편도/오프셋 안정성, 시리얼 vs UDP 비교,
꼬리지연(p99) 분석 + 시각화.

## 한계 (정직하게)

- 편도지연은 경로 대칭 가정 하의 근사다. 비대칭 경로에선 오프셋·편도가 편향된다.
- 시리얼은 편도 분리를 안 한다(왕복이 지표). USB-CDC 는 호스트 스케줄링·버퍼링이
  섞이므로, 맥↔Arduino 와 Pi↔Arduino 수치를 직접 비교하지 말고 각자 베이스라인으로.
