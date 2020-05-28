#include "ESP8266WiFi.h"
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <WiFiManager.h>          //https://github.com/tzapu/WiFiManager WiFi Configuration Magic

#define MAX_SRV_CLIENTS 4
#define RXBUFFERSIZE 1024
#define STACK_PROTECTOR  512 // bytes

#define IN_PIN 5 //D1
#define UDP_PORT 22222
#define UDP_HOST "192.168.1.137"
#define HOSTNAME "esp-2bus"
 
WiFiClient serverClients[MAX_SRV_CLIENTS];
WiFiUDP Udp;

#define BUFLEN 4096 // has to be pow of 2

uint16 frame[BUFLEN];
uint32 p = 0, last = 0;

void ICACHE_RAM_ATTR intPin() {
  frame[p%BUFLEN] = (micros() & 0xfffffe) | digitalRead(IN_PIN);
  p++;
}
 
void setup() {
  Serial.begin(9600);

  WiFiManager wifiManager;

  //wifiManager.resetSettings();

  wifiManager.setConfigPortalTimeout(120);
  wifiManager.autoConnect(HOSTNAME);

  ArduinoOTA.begin();

  //ESP.wdtDisable();
  MDNS.setHostname(HOSTNAME);

  Udp.begin(UDP_PORT);

  pinMode(IN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(IN_PIN), intPin, CHANGE);

  Udp.beginPacket(UDP_HOST, UDP_PORT);
  Udp.write("hello");
  Udp.endPacket();

  for (int i=0; i<BUFLEN; i++){
    frame[i]=i;
  }

}

int lastreport = 0;

int min(int a, int b){
  if (a < b){
    return a;
  }
  return b;
}

void loop() {
  ArduinoOTA.handle();

  if (last == UINT64_MAX){
    last = 0;
  }

  if (p != last){
    int to_send = min(600, p-last);
    int start = last%BUFLEN;
    if (p<last){
      to_send = min(600, UINT64_MAX - last);
    }

    /*
    Serial.print("tosend ");
    Serial.print(start);   
    Serial.print(" ");   
    Serial.println(to_send);
    */
    Udp.beginPacket(UDP_HOST, UDP_PORT);
    Udp.write((uint8_t*)(&frame[start]), 2*to_send);
    Udp.endPacket();
    last += to_send;
  }

  if (lastreport + 1000 < millis()){
    Serial.println(p);
    lastreport = millis();
  }

  //ESP.wdtFeed();

  if (WiFi.status() != WL_CONNECTED) {
    ESP.reset();
  }

}
