#include "secure_framing.h"
#include <openssl/hmac.h>
#include <openssl/crypto.h>

static const char *NAMES[] = {"OK","TOO_SHORT","BAD_MAGIC","BAD_VERSION",
                              "BAD_LENGTH","BAD_CRC","BAD_HMAC"};
const char *sf_reason_name(sf_reason r){ return NAMES[(int)r]; }

/* zlib 호환 CRC-32 (poly 0xEDB88320, init/xorout 0xFFFFFFFF). */
static uint32_t crc32_calc(const uint8_t *p, size_t n){
    static uint32_t table[256]; static int init = 0;
    if(!init){
        for(uint32_t i=0;i<256;i++){ uint32_t c=i;
            for(int k=0;k<8;k++) c = (c&1) ? (0xEDB88320u ^ (c>>1)) : (c>>1);
            table[i]=c; }
        init=1;
    }
    uint32_t c = 0xFFFFFFFFu;
    for(size_t i=0;i<n;i++) c = table[(c ^ p[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

sf_reason sf_decode(const uint8_t *buf, size_t len,
                    const uint8_t *key, size_t keylen, sf_decoded *out){
    if(len < SF_MIN_FRAME) return SF_TOO_SHORT;

    /* 1) HMAC 을 버퍼 끝 16바이트에서 잡아 먼저 검증 (인증 전엔 무신뢰). */
    size_t signed_len = len - SF_HMAC_LEN;
    const uint8_t *tag = buf + signed_len;
    uint8_t expect[32]; unsigned int elen = 0;
    if(!HMAC(EVP_sha256(), key, (int)keylen, buf, signed_len, expect, &elen))
        return SF_BAD_HMAC;
    if(CRYPTO_memcmp(tag, expect, SF_HMAC_LEN) != 0) return SF_BAD_HMAC;

    /* 2) CRC32 (magic..payload). */
    size_t integ_len = signed_len - SF_CRC_LEN;
    const uint8_t *cf = buf + integ_len;
    uint32_t crc_field = ((uint32_t)cf[0]<<24)|((uint32_t)cf[1]<<16)|((uint32_t)cf[2]<<8)|cf[3];
    if(crc32_calc(buf, integ_len) != crc_field) return SF_BAD_CRC;

    /* 3) 인증된 헤더 필드 검사. */
    if(buf[0]!='G' || buf[1]!='R') return SF_BAD_MAGIC;
    if(buf[2]!=1)                  return SF_BAD_VERSION;
    uint64_t seq = 0; for(int i=0;i<8;i++) seq = (seq<<8) | buf[3+i];
    uint16_t plen = ((uint16_t)buf[11]<<8) | buf[12];
    if((size_t)SF_HEADER_LEN + plen != integ_len) return SF_BAD_LENGTH;

    if(out){ out->seq=seq; out->payload=buf+SF_HEADER_LEN; out->payload_len=plen; }
    return SF_OK;
}
