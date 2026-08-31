# robot-link-timing — 분산 로봇 링크 타이밍 특성화

> *2026 · 단독 · 통신 축*
>
> grippers/Immortan 의 실제 통신 경로 **UDP(Host↔Pi)** 와 **시리얼(Pi↔STM32)** 의
> 지연·지터·클럭오프셋·손실·재정렬을 계측한다. *"증상이 아니라 계측"* — 2023 5G/UDP,
> 2026 RoboSec 로 이어온 통신 축을 **측정 데이터**로 잇는다.

---

## Problem

분산 로봇에서 "명령이 늦다/놓친다"는 증상은 흔하지만, 어느 링크가 얼마나 기여하는지는
재봐야 안다. 실제 경로는 두 개다 — 맥(Host)↔Pi 의 **UDP**, Pi↔STM32 의 **시리얼**.
하드웨어 종료(2026-09-08) 전에 **로그만** 확보하면 분석·시각화는 전부 오프라인이다.

## Architecture

```
[Host=맥] --UDP--> [Pi] --Serial--> [STM32]      참고 기준선: [Host]--USB--[Arduino Uno echo]
```

## My Contribution

- `udp_probe.py` — UDP 왕복 + **편도·클럭오프셋**(NTP식 4-타임스탬프) + 지터 + 손실·재정렬.
  측정 정의: RTT `=(T3-T0)-(T2-T1)`(응답 처리시간 제외), offset `=((T1-T0)+(T2-T3))/2`,
  지터 = 평균 `|ΔRTT|`(RFC3550 근사).
- `serial_probe.py` + `arduino/serial_echo/` — 시리얼 왕복·지터·손실.

## Verification (도구 자체 검증)

- **UDP 루프백** — 500/500, RTT mean **0.265 ms**. 프로버·리스폰더 로직과 오프셋 추정이
  옳게 도는지 로컬에서 확인.
- **시리얼 기준선(맥↔Arduino Uno echo)** — 1000/1000, 왕복 mean **7.08 ms**, p95 8.3,
  지터 0.014 ms. Uno echo 는 펌웨어 처리시간이 최소라 **USB-serial 링크 자체의 하한**을 준다.

## Limitations

- **실기 캡처(Pi↔STM32 부하 스윕)는 아직 못 했다.** 검증된 것은 도구 자체(UDP 루프백)와
  로봇 밖 통제 기준선(Uno echo)뿐이다. 실제 로봇 링크 값은 하드웨어로만 나오고,
  접근이 2026-09-08 에 끝난다 — 정직하게 한계로 둔다.
- STM32 는 실험용 echo 를 하지 않으므로, 실기 시리얼은 기존 프로토콜 명령→응답을
  passive 로 계측해야 한다(설계는 했고 실행은 미완).

## Future Work

- idle · 중간(perception) · 고부하(perception+모터+주행) **3단계 부하 스윕** 로그 확보.
- 오프라인: 지연 분포·지터·손실률의 부하 의존성, 편도/오프셋 안정성, 시리얼 vs UDP 비교.

---

**코드**: [`code/robot-link-timing/`](../code/robot-link-timing/) ·
**관련**: [5G/UDP 프로토타입](5g-udp-prototype.md) · [RoboSec](robosec.md) ·
[임베디드 시리얼 벤치](embedded-serial-bench.md)
