#!/usr/bin/env python3
"""AFL++ 시드 코퍼스 생성 — Python 레퍼런스로 유효/경계 프레임을 seeds/ 에 바이너리로 쓴다.

gen_vectors.py 와 같은 프레임을 쓰되, AFL 은 파일 코퍼스를 입력으로 받으므로
각 케이스를 개별 파일로 저장한다. 유효 프레임을 시드로 주면 퍼저가 HMAC·CRC·
길이 필드 구조를 빨리 학습해 인증 경계 안쪽까지 파고든다.
"""
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
# afl -> native -> udp-network-lab/protocol
sys.path.insert(0, str(here.parent.parent / "protocol"))
import secure_framing as F  # noqa: E402

KEY = b"grippers-preshared-key-2026"


def main() -> int:
    seeds = here / "seeds"
    seeds.mkdir(exist_ok=True)

    valid = F.encode({"state": "APPROACH", "linear_x": 0.1}, 1, KEY)
    flip_tag = bytearray(valid)
    flip_tag[-1] ^= 1
    flip_payload = bytearray(valid)
    flip_payload[15] ^= 1

    cases = {
        "valid": bytes(valid),
        "bad_hmac": bytes(flip_tag),
        "bad_payload": bytes(flip_payload),
        "too_short": bytes(valid[:20]),
        "empty": b"",
    }
    for name, frame in cases.items():
        (seeds / name).write_bytes(frame)
    print(f"시드 {len(cases)}개 -> {seeds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
