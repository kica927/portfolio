/* AFL++ persistent-mode 하네스 — sf_decode 를 리눅스 데스크탑에서 퍼징한다.
 *
 * libFuzzer 하네스(../fuzz_decode.c)와 **같은 진입점(sf_decode)** 을 겨눠,
 * 두 퍼저의 커버리지·발견을 비교하는 것이 목적이다. libFuzzer 는 맥에서
 * 1,300만 회 크래시 0 을 이미 확인했고, AFL++ 는 계측이 매끄러운 리눅스
 * 데스크탑에서 돌린다(맥 Apple Silicon 은 afl-clang-fast 설치가 까다로움).
 *
 * __AFL_FUZZ_INIT / __AFL_LOOP / __AFL_FUZZ_TESTCASE_* 는 afl-clang-fast 가
 * 정의하는 매크로다 — 일반 컴파일러로는 빌드되지 않는다(의도된 것).
 */
#include <stddef.h>
#include <stdint.h>
#include "secure_framing.h"

static const uint8_t KEY[] = "grippers-preshared-key-2026";

__AFL_FUZZ_INIT();

int main(void) {
#ifdef __AFL_HAVE_MANUAL_CONTROL
    __AFL_INIT();
#endif
    const uint8_t *buf = __AFL_FUZZ_TESTCASE_BUF;
    while (__AFL_LOOP(100000)) {
        size_t len = (size_t)__AFL_FUZZ_TESTCASE_LEN;
        sf_decoded out;
        sf_decode(buf, len, KEY, sizeof(KEY) - 1, &out);
    }
    return 0;
}
