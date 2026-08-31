# soarm-hardware-interface — SO-ARM101 실물 ros2_control (STS3215)

> *2026 · 단독 · 로봇팔 트랙 · 실기 연결 계층*
>
> [MoveIt 2 설정](moveit-so101.md)은 지금 `mock_components/GenericSystem` 으로 돈다.
> 이 패키지는 Feetech **STS3215** 시리얼 버스를 ros2_control `SystemInterface` (C++
> 플러그인)로 감싸, MoveIt 이 계획한 궤적을 **실물 SO-ARM101** 에서 실행하게 한다.
> mock↔실물은 xacro 인자 하나로 전환한다.

---

## Problem

MoveIt 은 궤적을 계획하지만, 그 궤적을 실제 서보로 내보내는 것은 ros2_control 의
하드웨어 인터페이스다. SO-ARM101 의 STS3215 는 벤더 ROS 드라이버가 없어, half-duplex
UART 프로토콜을 직접 `SystemInterface` 로 구현해야 실물 구동이 된다.

## My Contribution

`src/sts3215_system.cpp` 를 직접 작성했다 — Feetech half-duplex UART 프로토콜을
**termios 로 포팅**하고 ros2_control 수명주기에 얹었다.

## Implementation

- 패킷 `[0xFF 0xFF ID Len Inst Params ~checksum]`, PING/READ/WRITE, u16 LE, baud 1e6.
- `read()` PRESENT_POSITION(56) → rad, `write()` rad → GOAL_POSITION(42).
- `on_activate` 에서 토크 ON + **현재 위치를 명령 초기값으로** 잡아 급발진을 막는다.
- 프로토콜 상수는 grippers 의 `driver_sdk.py` 와 대조해 맞췄다(12bit 0..4095).
- `urdf/so101.ros2_control.xacro` 가 `use_mock` 인자로 mock↔실물을 가른다.

## Verification

- **데스크탑에서 colcon 빌드 성공**(ROS 2 Jazzy + ros2_control) — 플러그인이 정상
  등록·로드된다. `use_mock:=true` 면 기존 mock 데모로 즉시 회귀(안전한 폴백).

## Limitations

- **실물 미검증 골격이다.** 시리얼 왕복·폐루프는 실기에서 확인해야 하는데,
  하드웨어 접근이 2026-09-08 에 끝나 아직 못 했다 — 정직하게 한계로 둔다.
- 위치 제어만(속도·전류 미노출). MoveIt JTC 위치 궤적엔 충분하다.
- rad↔counts 는 `(pos-2048)·2π/4096` 선형 가정. 그리퍼는 링키지라 별도 매핑 필요(TODO).

## Future Work (9/8 전 실기 브링업 체크리스트)

1. 포트·권한 확인 → **팔을 받침대에 올리고** 토크 ON(초기 위치 튐 확인).
2. 한 관절 작은 목표각 → read 폐루프 확인 → 전 관절.
3. MoveIt 짧은 궤적 1개 → **영상 + `/joint_states` bag 녹화**(증빙).
4. 안 되면 read-only(관절 상태 스트림)만이라도 확보.

---

**코드**: [`code/soarm-hardware-interface/`](../code/soarm-hardware-interface/) ·
**관련**: [MoveIt 2 설정](moveit-so101.md) · [로봇팔 트랙](soarm-robotarm-track.md) ·
[컵 정렬](cup-sorting.md)
