/* secure_framing — Python 레퍼런스(protocol/secure_framing.py)의 C 재구현.
 * 프레이밍/암호 계층만 다룬다(JSON 파싱은 애플리케이션 몫). */
#ifndef SECURE_FRAMING_H
#define SECURE_FRAMING_H
#include <stddef.h>
#include <stdint.h>

typedef enum {
    SF_OK = 0, SF_TOO_SHORT, SF_BAD_MAGIC, SF_BAD_VERSION,
    SF_BAD_LENGTH, SF_BAD_CRC, SF_BAD_HMAC
} sf_reason;

typedef struct { uint64_t seq; const uint8_t *payload; uint16_t payload_len; } sf_decoded;

#define SF_HEADER_LEN 13   /* magic(2)+ver(1)+seq(8)+len(2) */
#define SF_HMAC_LEN   16
#define SF_CRC_LEN    4
#define SF_MIN_FRAME  (SF_HEADER_LEN + SF_CRC_LEN + SF_HMAC_LEN)  /* 33 */

const char *sf_reason_name(sf_reason r);
sf_reason sf_decode(const uint8_t *buf, size_t len,
                    const uint8_t *key, size_t keylen, sf_decoded *out);
#endif
