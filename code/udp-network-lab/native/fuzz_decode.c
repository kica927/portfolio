/* libFuzzer 타깃 — sf_decode 가 임의 입력에 메모리 오류 없이 도는지. */
#include "secure_framing.h"
static const uint8_t KEY[] = "grippers-preshared-key-2026";
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size){
    sf_decoded out;
    sf_decode(data, size, KEY, sizeof(KEY)-1, &out);
    return 0;
}
