#include <SPI.h>               
#include <LoRa.h>
#include <Wire.h> 
#include <WiFi.h>
#include "ThingSpeak.h"
#include "SSD1306Wire.h" 
SSD1306Wire display(0x3c, 8, 9); // ADDRESS, SDA, SCL
char ssid[] = "PhoneAP";             // your network SSID (name)
char pass[] = "smartcomputerlab";    // your network password (use for WPA, or use as key for WEP)

WiFiClient  client;

#define SCK     6   // GPIO18 -- SX127x's SCK
#define MISO    5   // GPIO19 -- SX127x's MISO
#define MOSI    7   // GPIO23 -- SX127x's MOSI
#define SS      4   // GPIO05 -- SX127x's CS
#define RST     10   // GPIO15 -- SX127x's RESET
#define DI0     2   // GPIO25 (integrated modem)  -- SX127x's IRQ(Interrupt Request)

typedef union
{
  uint8_t buff[28];
  struct
  {
    uint32_t  freq;         // GW - link frequency
    uint8_t   power;        // GW - emission power
    uint8_t   sf;           // GW - link spreading factor
    uint32_t  bw;           // GW - link signal bandwidth: [125E3, 250E3,500E3]
    uint8_t   cr;           // GW - link coding rate: [5,6,7,8] in function
    uint8_t   aeskey[16];   // GW - AES key
    uint8_t   pad;
  } par;
} gw_lora_t;
gw_lora_t gwlora;

typedef union 
{
 uint8_t frame[58]; 
 struct
  {
   uint32_t    channel;
   uint8_t     flag[2];
   char        wkey[16];
   uint32_t    number;
   float       sens[8]; 
  } pay;
} pack_t;

void display_SSD1306(int chan,float d1,float d2,float d3, int del) 
{
  char buff0[32],buff1[32],buff2[32];
  Wire.begin(8,9);
  display.init();
  //display.flipScreenVertically();
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.setFont(ArialMT_Plain_10);
  sprintf(buff0,"CH: %d",chan);
  sprintf(buff1,"T: %2.2f, H: %2.2f",d1,d2);
  sprintf(buff2,"L: %6.2f",d3);
  display.drawString(0, 4, buff0);
  display.drawString(0, 22, buff1);
  display.drawString(0, 36, buff2);
  display.drawString(20, 52, "SmartComputerLab");
  display.display();
//  delay(del*1000);  // display during del seconds 
//  display.displayOff();  // disconnecting display circuit
//  Wire.end();
}

int rssi;

void setLoRaPar()         // set LoRa radio parameters
{
  gwlora.par.freq= 868E6;
  gwlora.par.sf= 7;
  gwlora.par.bw= 125E3;
  gwlora.par.cr=5;
}

void setup() 
{
  Serial.begin(9600);  
  WiFi.mode(WIFI_STA); 
  WiFi.begin(ssid, pass);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);delay(100);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print(".");}
  Serial.println("");
  Serial.println("Connected to WiFi");  
  ThingSpeak.begin(client); // connexion (TCP) du client au serveur
  delay(1000);
  Serial.println("ThingSpeak begin");              
  SPI.begin(SCK,MISO,MOSI,SS);
  LoRa.setPins(SS,RST,DI0);
  setLoRaPar();
  Serial.println();delay(100);Serial.println();
  Serial.printf("LoRa freq: %d\n",gwlora.par.freq);
  Serial.printf("LoRa sf: %d\n",gwlora.par.sf);
  Serial.printf("LoRa bw: %d\n",gwlora.par.bw);
  Serial.printf("LoRa cr: %d\n",gwlora.par.cr);
  if (!LoRa.begin(gwlora.par.freq)) {
    Serial.println("Starting LoRa failed!");
    while (1);}
  Serial.println("Starting LoRa OK!");delay(1000);
  LoRa.setSpreadingFactor(gwlora.par.sf);
  LoRa.setSignalBandwidth(gwlora.par.bw);
  LoRa.setCodingRate4(gwlora.par.cr);
}

uint32_t slast=0;  // last millis 
  
void loop() 
{
 pack_t qrdp;  
 int i;
  int packetSize = LoRa.parsePacket();
  if(packetSize==58)
    {
    i=0;
    while (LoRa.available())  {  qrdp.frame[i]=LoRa.read();i++; }
    rssi=LoRa.packetRssi();
    display_SSD1306(qrdp.pay.channel,qrdp.pay.sens[0],qrdp.pay.sens[1],qrdp.pay.sens[2],5); 
    if(millis()>(slast+20000))
      {
      slast=millis(); 
      Serial.printf("Channel ID: %d\n",qrdp.pay.channel);
      Serial.print(qrdp.pay.flag[0],HEX);Serial.println(qrdp.pay.flag[1],HEX);
      Serial.printf("WKEY: %16.16s\n",qrdp.pay.wkey);
      Serial.printf("temp:%2.2f,humi=%2.2f,lumi=%.2f, bat=%.2f\n",qrdp.pay.sens[0],qrdp.pay.sens[1],qrdp.pay.sens[2],qrdp.pay.sens[3]);
      Serial.printf("number: %d\n",qrdp.pay.number);
 
      if(qrdp.pay.flag[0]&0x80) ThingSpeak.setField(1,qrdp.pay.sens[0]);  //qrdp.pay.sens[0]); 
      if(qrdp.pay.flag[0]&0x40) ThingSpeak.setField(2,qrdp.pay.sens[1]); // qrdp.pay.sens[1]); 
      if(qrdp.pay.flag[0]&0x20) ThingSpeak.setField(3,qrdp.pay.sens[2]); 
      
      ThingSpeak.setField(4,rssi); 
      Serial.println("\nconnecting...");
      while (WiFi.status() != WL_CONNECTED) { delay(500);  }
      char wkey[17]; 
      strncpy(wkey,qrdp.pay.wkey,16);wkey[16]='\0';
      int x = ThingSpeak.writeFields(qrdp.pay.channel,wkey);
      if(x == 200){Serial.println("Channel update successful.");}
      else { Serial.println("Problem updating channel. HTTP error code " + String(x));}
      }
  }
}
