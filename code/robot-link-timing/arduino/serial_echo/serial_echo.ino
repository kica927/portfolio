// serial_echo — 링크 타이밍 프로브의 Arduino 쪽. 받은 프레임을 즉시 그대로 되돌린다.
// 프레임: 0x4C 0x54 (magic "LT") | seq(4B, big-endian) | payload(N)
// 호스트가 tx/rx 시각을 재므로 Arduino 는 최소 지연으로 echo 만 한다.
static const uint8_t MAGIC0 = 0x4C, MAGIC1 = 0x54;
uint8_t buf[256];
void setup() { Serial.begin(115200); }
void loop() {
  // 프레임 하나를 읽어 즉시 되쏜다. 길이는 호스트가 개행(0x0A)으로 구분.
  static int n = 0;
  while (Serial.available()) {
    uint8_t b = Serial.read();
    if (n < (int)sizeof(buf)) buf[n++] = b;
    if (b == 0x0A) {                 // 프레임 끝
      if (n >= 2 && buf[0] == MAGIC0 && buf[1] == MAGIC1) Serial.write(buf, n);
      n = 0;
    }
  }
}
