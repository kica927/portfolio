// serial-link-characterization — 길이 기반 echo. 프레임: 'L''T' len payload[len].
// BAUD 는 baud 스윕 때 빌드 전 치환된다.
#ifndef BAUD
#define BAUD 115200
#endif
uint8_t buf[260];
void setup() { Serial.begin(BAUD); Serial.setTimeout(50); }
void loop() {
  if (!Serial.available()) return;
  if (Serial.read() != 'L') return;
  uint8_t b;
  if (Serial.readBytes(&b, 1) != 1 || b != 'T') return;
  if (Serial.readBytes(&b, 1) != 1) return;
  uint8_t len = b;
  buf[0] = 'L'; buf[1] = 'T'; buf[2] = len;
  if (Serial.readBytes(buf + 3, len) != len) return;
  Serial.write(buf, 3 + len);
}
