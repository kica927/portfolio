// embedded-serial-security — Uno 측 프레이밍 디코더.
// udp-network-lab secure_framing 의 임베디드판(무결성 CRC32 + 재전송 시퀀스).
// HMAC-SHA256 은 ATmega328(8bit·2KB RAM)엔 무거워 여기선 제외 — README 에서 비용 논의.
//
// 프레임(host→Uno):  'S''F' | seq(u32 BE) | len(u8) | payload[len] | crc32(u32 BE)
// 응답(Uno→host):    'S''F' | status(u8) | seq(u32 BE)
//   status: 0x00 OK · 0x02 BAD_LEN · 0x03 BAD_CRC · 0x04 REPLAY · 0x05 TRUNCATED
static const uint8_t M0 = 0x53, M1 = 0x46, MAXLEN = 32;
uint32_t last_seq = 0; bool have_last = false;
uint8_t integ[7 + MAXLEN];

uint32_t crc32(const uint8_t *d, uint8_t n) {          // zlib 호환
  uint32_t c = 0xFFFFFFFFUL;
  for (uint8_t i = 0; i < n; i++) {
    c ^= d[i];
    for (uint8_t k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320UL ^ (c >> 1)) : (c >> 1);
  }
  return c ^ 0xFFFFFFFFUL;
}
void respond(uint8_t status, uint32_t seq) {
  uint8_t r[7] = {M0, M1, status,
                  (uint8_t)(seq >> 24), (uint8_t)(seq >> 16),
                  (uint8_t)(seq >> 8),  (uint8_t)seq};
  Serial.write(r, 7);
}
void setup() { Serial.begin(115200); Serial.setTimeout(50); }
void loop() {
  if (!Serial.available()) return;
  if ((uint8_t)Serial.read() != M0) return;            // 매직 동기화
  uint8_t b;
  if (Serial.readBytes(&b, 1) != 1 || b != M1) return; // 재동기화
  uint8_t hdr[5];
  if (Serial.readBytes(hdr, 5) != 5) return;           // 트렁케이트 → 조용히 버림
  uint32_t seq = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                 ((uint32_t)hdr[2] << 8) | hdr[3];
  uint8_t len = hdr[4];
  if (len > MAXLEN) { respond(0x02, seq); return; }     // BAD_LEN
  integ[0] = M0; integ[1] = M1;
  integ[2] = hdr[0]; integ[3] = hdr[1]; integ[4] = hdr[2]; integ[5] = hdr[3]; integ[6] = len;
  if (Serial.readBytes(integ + 7, len) != len) { respond(0x05, seq); return; }  // TRUNCATED
  uint8_t crcb[4];
  if (Serial.readBytes(crcb, 4) != 4) { respond(0x05, seq); return; }
  uint32_t crc_rx = ((uint32_t)crcb[0] << 24) | ((uint32_t)crcb[1] << 16) |
                    ((uint32_t)crcb[2] << 8) | crcb[3];
  if (crc32(integ, 7 + len) != crc_rx) { respond(0x03, seq); return; }           // BAD_CRC
  if (have_last && seq <= last_seq)   { respond(0x04, seq); return; }            // REPLAY
  last_seq = seq; have_last = true;
  respond(0x00, seq);                                                            // OK
}
