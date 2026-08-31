"""Python 레퍼런스로 차등 검증 벡터를 만든다 (native/vectors.txt)."""
import sys, struct, zlib, hmac, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "protocol"))
import secure_framing as F

KEY = b"grippers-preshared-key-2026"

def craft(magic, ver, seq, len_field, payload):
    head = struct.pack(">2sBQH", magic, ver, seq, len_field)
    integ = head + payload
    crc = struct.pack(">I", zlib.crc32(integ) & 0xFFFFFFFF)
    signed = integ + crc
    tag = hmac.new(KEY, signed, "sha256").digest()[:16]
    return signed + tag

p = b'{"state":"APPROACH"}'
valid = F.encode({"state": "APPROACH", "linear_x": 0.1}, 1, KEY)
flip_tag = bytearray(valid); flip_tag[-1] ^= 1
flip_payload = bytearray(valid); flip_payload[15] ^= 1

cases = [
    valid,                              # OK
    bytes(flip_tag),                    # BAD_HMAC
    valid[:20],                         # TOO_SHORT
    craft(b"XX", 1, 1, len(p), p),      # BAD_MAGIC
    craft(b"GR", 2, 1, len(p), p),      # BAD_VERSION
    craft(b"GR", 1, 1, len(p)+1, p),    # BAD_LENGTH
    bytes(flip_payload),                # BAD_HMAC (페이로드 변조)
]
lines = [f"{F.decode(fr, KEY).reason.name} {fr.hex()}" for fr in cases]
out = pathlib.Path(__file__).resolve().parent / "vectors.txt"
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
