"""grippers Host↔Pi 링크 프로토콜 — 공격자 관점의 독립 재구현.

이 파일은 grippers 저장소를 import 하지 않는다. 공격자가 아는 것은 **규격뿐**
이라는 전제를 지키기 위해서다. 규격의 단일 소스는 Host 쪽
`VEHICLE_LINK_PROTOCOL.md` 이고, Pi 쪽 수신부는
`domain/adapters/real/udp_host_link.py` 다.

프로토콜 요약 (2026-08-26 확정):
  - 전송: UDP. 명령 5005, 보고 5006.
  - 명령 페이로드: UTF-8 JSON, 다섯 필드
        state(str) · linear_x · linear_y · angular_z(float) · stop(bool)
  - 무결성 검사 없음 · 시퀀스 번호 없음 · 타임스탬프 없음 · 송신자 인증 없음.

이 "없음" 셋이 RoboSec 이 겨누는 공격면(A1~A3)의 뿌리다.
"""

from __future__ import annotations

import json

COMMAND_PORT = 5005
STATUS_PORT = 5006

VALID_STATES = (
    "IDLE", "APPROACH", "GRASP", "CARRY", "APPROACH_BOX", "INSERT", "DONE", "ESTOP",
)

# Pi 가 실제로 집행하는 속도 상한 (domain/task/motion.py). 공격이 이 값을
# 넘겨도 클램프되는지를 보기 위해 알아 둔다 — 방어값이지 규격값이 아니다.
AGREED_LINEAR_MPS = 0.1
AGREED_ROTATION_RAD_S = 0.25
BASKET_APPROACH_MPS = 0.06


def command(state: str, linear_x: float = 0.0, linear_y: float = 0.0,
            angular_z: float = 0.0, stop: bool = False) -> bytes:
    """규격에 맞는 명령 한 개를 바이트로 만든다."""
    body = {
        "state": state,
        "linear_x": float(linear_x),
        "linear_y": float(linear_y),
        "angular_z": float(angular_z),
        "stop": bool(stop),
    }
    return json.dumps(body).encode("utf-8")


def raw(obj) -> bytes:
    """임의 객체를 JSON 으로 — 규격을 벗어난 명령을 만들 때 쓴다."""
    return json.dumps(obj).encode("utf-8")
