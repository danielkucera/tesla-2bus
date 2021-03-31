#include <Arduino.h>

#define RST PB6
#define SWDIO PB14
#define SWCLK PB13
#define SWIM PB11
#define LED PA9

#define IN_PIN SWDIO
#define OUT_PIN SWCLK

long start = 0;
int pulse_len = 0;
int pulse_cnt = 0;

uint32_t last_fall = 0;
uint32_t fall_len = 0;

#define BUFLEN 2048

unsigned char buffer[BUFLEN];
int pos = 0;

void falling() {
  if (pos + 5 > BUFLEN) {
    return;
  }
  uint32_t now = micros();
  fall_len = now - last_fall;
  last_fall = now;
  if (fall_len > 0xfe){
    unsigned char* flc = (unsigned char*)&fall_len;
    buffer[pos++] = 0xff;
    buffer[pos++] = flc[0];
    buffer[pos++] = flc[1];
    buffer[pos++] = flc[2];
    buffer[pos++] = flc[3];
  } else {
    buffer[pos++] = (unsigned char)fall_len;
  }
}

void setup() {
    // put your setup code here, to run once:
    Serial.begin(115200);
    Serial.println("START");
    pinMode(LED, OUTPUT);
    pinMode(IN_PIN, INPUT);
    digitalWrite(IN_PIN, 0); // pull-down 40k divider with external 2k to VCC
    attachInterrupt(digitalPinToInterrupt(IN_PIN), falling, FALLING);

    pinMode(OUT_PIN, OUTPUT);
    digitalWrite(OUT_PIN, 0);
  }

void writeSymbol(int bit){
  int hi, lo;
  if (bit == 1) {
    hi = 37;
    lo = 33;
  } else if (bit == 0) {
    hi = 67;
    lo = 59;
  } else {
    hi = 50;
    lo = 50;
  }
  for (int i=0; i<4; i++){
    delayMicroseconds(hi);
    digitalWrite(OUT_PIN, 1);
    delayMicroseconds(lo);
    digitalWrite(OUT_PIN, 0);
  }
}

void writePreamble(){
  for (int i=0; i<60; i++){
    writeSymbol(-1);
  }
}

void writeByte(u_char b){
  for (int i=0; i<8; i++){
    writeSymbol(b & 1);
    writeSymbol(-1);
    b = b >> 1;
  }
}

uint32_t last;

void loop() {
  if (micros() > last + 500){
    last = micros();
//    Serial.print("fall len ");      Serial.println(fall_len);
    if (pos > 0){
      Serial.write(buffer, pos);
      Serial.flush();
      pos = 0;
    }
  }

  if ((Serial.available() > 0) && (micros() > last_fall + 1000)){
    writePreamble();
    while (Serial.available() > 0){
      char b = Serial.read();
      writeByte(b);
    }
  }

}
