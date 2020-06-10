#include "ESP8266WiFi.h"
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <WiFiManager.h>          //https://github.com/tzapu/WiFiManager WiFi Configuration Magic

#define MAX_SRV_CLIENTS 4
#define RXBUFFERSIZE 1024
#define STACK_PROTECTOR  512 // bytes

#define IN_PIN 5 //D1
#define HOSTNAME "esp-2bus"
 
WiFiClient serverClients[MAX_SRV_CLIENTS];
WiFiServer wifiServer(22222);

#define BUFLEN 4096 // has to be pow of 2

uint8 frame[BUFLEN];
uint32 p = 0, last = 0;
uint32 edge = 0;

void ICACHE_RAM_ATTR intPin() {
  uint32 cedge = micros();
  frame[p%BUFLEN] = cedge - edge;
  edge = cedge;
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

  wifiServer.begin();

  pinMode(IN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(IN_PIN), intPin, FALLING);

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

  //check if there are any new clients
  if (wifiServer.hasClient()) {
    //find free/disconnected spot
    int i;
    for (i = 0; i < MAX_SRV_CLIENTS; i++)
      if (!serverClients[i]) { // equivalent to !serverClients[i].connected()
        serverClients[i] = wifiServer.available();
        break;
      }

    //no free/disconnected spot so reject
    if (i == MAX_SRV_CLIENTS) {
      wifiServer.available().println("busy");
      // hints: server.available() is a WiFiClient with short-term scope
      // when out of scope, a WiFiClient will
      // - flush() - all data will be sent
      // - stop() - automatically too
    }
  }

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
    for (int i = 0; i < MAX_SRV_CLIENTS; i++){
      // if client.availableForWrite() was 0 (congested)
      // and increased since then,
      // ensure write space is sufficient:
      if (serverClients[i].availableForWrite() >= 1) {
        serverClients[i].write((uint8_t*)(&frame[start]), to_send);
      }
    }

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
