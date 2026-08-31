# AFL++ 퍼징 — sf_decode

libFuzzer(맥, 1,300만 회 크래시 0)와 **탐색 전략이 다른** AFL++ 로 `sf_decode` 를 한 번
더 퍼징해 사각을 줄인다. 같은 진입점을 두 도구로 보면 서로의 빈틈을 메운다.

## 실행 결과 (2026-08-31, 맥 Apple Silicon M-series)

| | libFuzzer | AFL++ |
|---|---|---|
| 실행 수 | 13,020,000+ | **7,353,796** (60초) |
| 속도 | — | **122,561 exec/s** (persistent mode) |
| 커버리지 | — | bitmap 39.47% |
| 크래시 / 행 | 0 | **0 / 0** |

두 퍼저 모두 **크래시·행 0** — `sf_decode` 는 임의 입력에 메모리 오류 없이 돈다.
낮은 커버리지(39%)는 인증(HMAC) 앞단에서 대부분 잘려 나가는, 좁은 공격면을 그대로 뜻한다.

## 실행 — 맥 (Apple Silicon)

맥도 되지만 두 가지 선행이 필요하다: AFL++ 설치, 그리고 **SysV 공유메모리 한계 상향**
(macOS 기본값이 작아 fork server 가 shmget 에 실패한다). 후자는 sudo 가 필요하다.

```
brew install afl++
sudo afl-system-config
SSL=/opt/homebrew/opt/openssl@3
AFL_USE_ASAN=1 afl-clang-fast -O2 -g -I.. -I"$SSL/include" afl_harness.c ../secure_framing.c -o fuzz_decode_afl -L"$SSL/lib" -lcrypto
python3 make_seeds.py
AFL_NO_UI=1 afl-fuzz -i seeds -o out -m none -V 60 -- ./fuzz_decode_afl
```

`sudo afl-system-config` 는 공유메모리 sysctl(`kern.sysv.shm*`)을 늘리고 crash reporter
(ReportCrash)를 내린다. ASAN 빌드라 `-m none` 이 필요하다.

## 실행 — 리눅스

`run_afl.sh` 참고(`sudo apt install afl++ libssl-dev clang`, `SSL` 기본 `/usr`).

## 파일

- `afl_harness.c` — AFL++ persistent 하네스. libFuzzer 하네스와 **같은 진입점(`sf_decode`)**.
  `unistd.h` 가 필요하다(`__AFL_FUZZ_TESTCASE_LEN` 매크로가 `read()` 를 쓴다 — 맥 clang 이
  이 누락을 잡아 고쳤다).
- `make_seeds.py` — 유효/경계 프레임 시드.
- `run_afl.sh` — 리눅스 러너.
- 결과는 `out/` — `out/default/crashes/` 가 비어 있어야 정상.
