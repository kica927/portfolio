#!/usr/bin/env bash
# 리눅스 데스크탑 전용 — AFL++ 로 sf_decode 를 퍼징한다.
#
# 선행: sudo apt install afl++ clang libssl-dev python3
# 실행: bash run_afl.sh            (Ctrl-C 로 종료, 결과는 out/ 에)
#
# 맥(Apple Silicon)에서는 afl-clang-fast 계측 설치가 까다로워 여기서 돌리지
# 않는다 — libFuzzer 는 맥에서 이미 1,300만 회 돌렸고(../fuzz_decode.c),
# 이 스크립트는 리눅스에서 AFL++ 커버리지를 따로 얻어 비교하기 위한 것이다.
set -euo pipefail
cd "$(dirname "$0")"

CC=${CC:-afl-clang-fast}
if ! command -v "$CC" >/dev/null 2>&1; then
    echo "[afl] $CC 없음 — 'sudo apt install afl++' 후 다시 실행하세요." >&2
    exit 1
fi

# 리눅스는 보통 시스템 openssl(/usr, libssl-dev). 다르면 SSL 로 덮어쓰세요.
SSL=${SSL:-/usr}

echo "[afl] 하네스 빌드 ($CC)"
"$CC" -O2 -g -I.. -I"$SSL/include" -fsanitize=address \
    afl_harness.c ../secure_framing.c -o fuzz_decode_afl -L"$SSL/lib" -lcrypto

echo "[afl] 시드 생성"
python3 make_seeds.py

echo "[afl] 퍼징 시작 — out/ 에 결과, Ctrl-C 로 종료"
AFL_SKIP_CPUFREQ=1 AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 \
    afl-fuzz -i seeds -o out -- ./fuzz_decode_afl
