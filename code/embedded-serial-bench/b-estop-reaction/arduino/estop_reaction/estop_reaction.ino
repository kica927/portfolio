// embedded-estop-reaction — 하드웨어 E-STOP 반응지연 측정.
// 배선: 점퍼선 D4 ── D2.  D4=자극 출력(active-low), D2=INT0 감지(FALLING).
// 반응지연 = D4 를 LOW 로 떨어뜨린 순간(t0) → D2 인터럽트 진입(t_isr).
//   = digitalWrite + 전파 + 인터럽트 지연. micros() 분해능 4µs.
volatile uint32_t t_isr; volatile bool fired;
void isr() { t_isr = micros(); fired = true; }
void setup() {
  Serial.begin(115200);
  pinMode(4, OUTPUT); digitalWrite(4, HIGH);        // 라인 유휴 = HIGH
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(2), isr, FALLING);
}
void loop() {
  if (!Serial.available()) return;
  if (Serial.read() != 'G') return;
  fired = false;
  uint32_t t0 = micros();
  digitalWrite(4, LOW);                             // E-STOP 자극(하강 에지)
  uint32_t reaction = 0xFFFFFFFFUL;                 // no-fire 표식(점퍼 없음)
  while (micros() - t0 < 5000) { if (fired) { reaction = t_isr - t0; break; } }
  digitalWrite(4, HIGH);                            // 라인 복귀
  delayMicroseconds(300);
  uint8_t r[4] = {(uint8_t)(reaction >> 24), (uint8_t)(reaction >> 16),
                  (uint8_t)(reaction >> 8), (uint8_t)reaction};
  Serial.write(r, 4);
}
