"""W2 — Atheris 퍼즈 하네스: secure_framing.decode 견고성.

불변식:
  1) decode 는 임의 바이트에 대해 **절대 예외를 던지지 않는다** (항상 Decoded).
  2) decode 가 ok 를 반환한 프레임은 재인코딩해도 여전히 ok 로 복호된다(멱등).

    ~/.venv_fuzz/bin/python fuzz/fuzz_framing.py -max_total_time=25
"""
import sys, atheris

with atheris.instrument_imports():
    sys.path.insert(0, "protocol")
    import secure_framing as F

KEY = b"grippers-preshared-key-2026"


def one(data: bytes):
    d = F.decode(data, KEY)          # 예외 나면 크래시로 잡힌다
    if d.ok:
        re = F.encode(d.payload, d.seq, KEY)
        d2 = F.decode(re, KEY)
        assert d2.ok, "ok 프레임의 재인코딩이 복호 실패 — 멱등성 깨짐"


def main():
    atheris.Setup(sys.argv, one)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
