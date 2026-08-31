# 퍼징 — W2(Atheris) · W3(C + libFuzzer)

> 2026-08-30 · Python 레퍼런스와 C 재구현을 각각 퍼즈하고, 둘을 차등 검증했다.

## W2 — Atheris (Python `secure_framing.decode`)

데스크탑(Linux, `~/.venv_fuzz`)에서 두 하네스를 각 25초:

| 하네스 | 대상 | 실행 | 크래시 | 비고 |
|---|---|---|---|---|
| [`fuzz/fuzz_framing.py`](fuzz/fuzz_framing.py) | 임의 바이트 → decode | **1,495만 회** | 0 | decode 예외 없음 + ok 프레임 멱등 |
| [`fuzz/fuzz_authed_payload.py`](fuzz/fuzz_authed_payload.py) | 올바로 서명한 임의 페이로드 | **402만 회** | 0 | 인증 뒤 JSON 파서까지 견고(cov 14→25) |

**관찰**: HMAC 이 첫 관문이라 무작위 입력은 파서에 **닿지도 못한다**(1차 cov 14).
이것은 버그가 아니라 설계 이득이다 — 인증 안 된 입력은 파싱 전에 잘린다. 파서
자체의 견고성은 2차 하네스(인증된 악성 페이로드)로 따로 확인했다.

## W3 — C 재구현 + libFuzzer

[`native/secure_framing.c`](native/secure_framing.c) — 같은 와이어 포맷의 C 디코더.
CRC32 는 zlib 호환 직접 구현, HMAC-SHA256 은 OpenSSL. 맥(Homebrew clang 23 +
openssl@3), `-fsanitize=fuzzer,address`.

| 산출물 | 결과 |
|---|---|
| [`native/sf_selftest.c`](native/sf_selftest.c) 차등 검증 | **7/7 C↔Python 일치** (OK·BAD_HMAC·TOO_SHORT·BAD_MAGIC·BAD_VERSION·BAD_LENGTH) |
| [`native/fuzz_decode.c`](native/fuzz_decode.c) libFuzzer 25초 | **1,302만 회**, 크래시·ASan 오류 0 |

차등 검증이 핵심이다: Python 레퍼런스가 만든 벡터를 C 가 **같은 사유**로 거부/수용
한다 — 두 구현이 같은 규격을 구현했음을 기계적으로 보인다. libFuzzer 는 임의
입력에 대한 **메모리 안전성**(OOB 읽기 없음)을 ASan 으로 확인한다.

```
cd native && python3 gen_vectors.py && make all
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/openssl@3/lib ./sf_selftest vectors.txt
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/openssl@3/lib ./fuzz_decode -max_total_time=25
```

## 정직하게 — 설계 비평

- **CRC32 는 HMAC 뒤에서 사실상 잉여다.** HMAC 이 magic..crc 전체를 덮으므로,
  인증을 통과한 프레임은 CRC 도 항상 맞는다. 공격자는 CRC 를 못 건드린다(HMAC
  이 먼저 막음). CRC 는 규격 완결성·계층 분리 목적으로 남겨 두되, 보안상 실효는
  HMAC 이 전담한다. 이 중복을 아는 채로 두는 것과 모르고 두는 것은 다르다.
- libFuzzer/Atheris 의 낮은 커버리지(raw 입력)는 곧 **공격면이 좁다는 뜻**이다 —
  인증 게이트가 퍼저조차 깊은 경로로 못 들여보낸다.
