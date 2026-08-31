"""W2(2) — 인증 뒤 파서 경로 퍼즈.

퍼저가 페이로드 바이트를 정한 뒤 올바른 CRC·HMAC 로 감싸 '인증된 프레임'을
만든다. 그러면 decode 가 HMAC/CRC/len 을 통과해 **json 파서까지** 도달하므로,
임의(악의) 페이로드에 대한 파싱 견고성을 직접 두들긴다.

불변식: decode 는 인증된-그러나-깨진 페이로드에도 예외 없이 Decoded 를 돌려준다
(BAD_JSON 이거나, 유효 JSON 이면 ok).

    ~/.venv_fuzz/bin/python fuzz/fuzz_authed_payload.py -max_total_time=25
"""
import sys, hmac, zlib, atheris

with atheris.instrument_imports():
    sys.path.insert(0, "protocol")
    import secure_framing as F

KEY = b"grippers-preshared-key-2026"


def sign(payload: bytes, seq: int) -> bytes:
    payload = payload[:0xFFFF]
    head = F._HEADER.pack(F.MAGIC, F.VERSION, seq & 0xFFFFFFFFFFFFFFFF, len(payload))
    integrity = head + payload
    crc = F._CRC.pack(zlib.crc32(integrity) & 0xFFFFFFFF)
    signed = integrity + crc
    tag = hmac.new(KEY, signed, "sha256").digest()[:F._HMAC_LEN]
    return signed + tag


def one(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    seq = fdp.ConsumeUInt(8)
    payload = fdp.ConsumeBytes(fdp.remaining_bytes())
    d = F.decode(sign(payload, seq), KEY)     # 예외 나면 크래시
    # 인증은 항상 통과해야 한다(우리가 올바로 서명했으므로). 그 뒤 결과는
    # ok(유효 JSON) 또는 BAD_JSON(깨진 페이로드) 둘 중 하나여야 한다.
    assert d.reason in (F.Reject.OK, F.Reject.BAD_JSON), f"예상 밖 사유 {d.reason}"


def main():
    atheris.Setup(sys.argv, one)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
