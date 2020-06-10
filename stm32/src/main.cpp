#include <Arduino.h>

#define RST PB6
#define SWDIO PB14
#define SWCLK PB13
#define SWIM PB11
#define LED PA9

#define IN_PIN SWDIO

long start = 0;
int pulse_len = 0;
int pulse_cnt = 0;

uint32_t last_fall = 0;
uint32_t fall_len = 0;

void falling() {
  uint32_t now = micros();
  fall_len = now - last_fall;
  last_fall = now;
  if (fall_len > 0xff){
    fall_len = 0xff;
  }
  Serial.write((unsigned char)fall_len);
}

void setup() {
    // put your setup code here, to run once:
    Serial.begin(115200);
    Serial.println("START");
    pinMode(LED, OUTPUT);
    pinMode(IN_PIN, INPUT);
    digitalWrite(IN_PIN, 0);

    attachInterrupt(digitalPinToInterrupt(IN_PIN), falling, FALLING);
}

int last_cnt = 0;
long last;

void loop() {

  if (millis() > last + 1000){
    last = millis();
//    Serial.print("fall len ");      Serial.println(fall_len);
  }

}
