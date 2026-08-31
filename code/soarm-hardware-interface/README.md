# soarm-hardware-interface — SO-ARM101 실물 MoveIt (STS3215 ros2_control)

> so101_moveit_config 는 지금 `mock_components/GenericSystem` 으로 돈다. 이 패키지는
> Feetech **STS3215** 시리얼 버스를 ros2_control `SystemInterface` 로 감싸, **MoveIt 이
> 계획한 궤적을 실물 SO-ARM101** 에서 실행하게 한다. mock↔실물은 xacro 인자 하나로 전환.

## 무엇을 직접 작성했나

- `src/sts3215_system.cpp` — Feetech half-duplex UART 프로토콜을 **termios 로 직접 포팅**
  (패킷 `[0xFF 0xFF ID Len Inst Params ~sum]`, 체크섬, PING/READ/WRITE, u16 LE),
  그리고 ros2_control 수명주기(on_init/configure/activate/read/write/deactivate).
  - `read()` PRESENT_POSITION(56) → rad, `write()` rad → GOAL_POSITION(42).
  - on_activate 에서 토크 ON + 현재 위치를 명령 초기값으로(급발진 방지).
- 프로토콜 상수는 grippers `soarm_lab/driver_sdk.py` 와 대조해 맞췄다(baud 1e6, 12bit 0..4095).

## 빌드 (데스크탑, ROS 2 Jazzy + ros2_control)

```
cp -r so101_hardware ~/so101_ws/src/
cd ~/so101_ws && colcon build --packages-select so101_hardware && source install/setup.bash
```

## MoveIt 데모에 연결

`so101_moveit_config` 의 ros2_control xacro 를 `urdf/so101.ros2_control.xacro` 로 교체하고:
```
ros2 launch so101_moveit_config demo.launch.py         # use_mock:=false 로 실물
```
`use_mock:=true` 면 기존 mock 데모로 즉시 회귀(안전한 폴백).

## 실기 브링업 체크리스트 (9/8 전)

1. `ls /dev/ttyACM*` 포트 확인, 권한(`dialout`).
2. **팔을 받침대에 올리고** 토크 ON — 초기 위치가 튀지 않는지.
3. 한 관절만 작은 목표각 → read 값이 따라오는지(폐루프 확인).
4. MoveIt 으로 짧은 궤적 1개 → **영상 + `/joint_states` bag 녹화**(포트폴리오 증빙).
5. 안 되면 read-only(관절 상태 스트림)만이라도 확보.

## 한계 / 주의

- 위치 제어만(속도·전류 미노출). MoveIt JTC 위치 궤적엔 충분.
- rad↔counts 는 `(pos-2048)·2π/4096` 선형 가정. 그리퍼는 링키지라 별도 매핑 필요(TODO).
- 실물 미검증 골격이다 — 빌드·시리얼 왕복은 데스크탑/실기에서 확인해야 한다.
- 안전: 첫 시도는 저속·단일관절, E-STOP(토크 OFF) 준비.
