#include <WiFi.h>
#include "ThingSpeak.h"
char ssid[] = "PhoneAP";             // your network SSID (name)
char pass[] = "smartcomputerlab";    // your network password (use for WPA, or use as key for WEP)
unsigned long myChannelNumber =1626377;   
const char *myWriteAPIKey="3IN09682SQX3PT4Z" ;
const char *myReadAPIKey="9JVTP8ZHVTB9G4TT" ;
#define LED_PIN   18
#define uS_TO_S_FACTOR 1000000ULL  /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP  20        /* Time ESP32 will go to sleep (in seconds) */
RTC_DATA_ATTR float temperature=0.0,humidity=0.0;

WiFiClient  client;

union {
  uint8_t frame[38];    // or frame[52] for full channel
  struct {
    uint32_t channel;   // TS channel number – identifier
    uint8_t  flag[2];   // TS channel field flag
    char     key[16];   // TS channel write or read key  
    float    sens[4];   // or sens[8] for full channel  
  } pay;
} sdp;       // packet to send

void setup() 
{  
//  pinMode(LED_PIN, OUTPUT);
//  digitalWrite(LED_PIN,HIGH);Serial.println();
  WiFi.mode(WIFI_STA); 
  Serial.begin(9600); 
  WiFi.begin(ssid, pass);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  while (WiFi.status() != WL_CONNECTED) {
      delay(500); Serial.print(".");
  }
  Serial.println("");
  Serial.println("Connected to WiFi");  
  ThingSpeak.begin(client); // connexion (TCP) du client au serveur
  delay(1000);
  Serial.println("ThingSpeak begin");
  sdp.pay.sens[0] = temperature;
  sdp.pay.sens[1] = humidity;
  sdp.pay.flag[0]=0xC0;sdp.pay.flag[1]=0x00;
  Serial.println("Fields update");
  if(sdp.pay.flag[0]&0x80) ThingSpeak.setField(1, sdp.pay.sens[0]);
  if(sdp.pay.flag[0]&0x40) ThingSpeak.setField(2, sdp.pay.sens[1]);
  int x = ThingSpeak.writeFields(myChannelNumber, myWriteAPIKey);
  if(x == 200){Serial.println("Channel update successful.");}
    else { Serial.println("Problem updating channel. HTTP error code " + String(x));} 
  temperature+=0.1; humidity+=0.2;
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32C3 to sleep for every " + String(TIME_TO_SLEEP) +" Seconds");
  Serial.println("Going to sleep now: start low_power stage");
  //digitalWrite(LED_PIN,LOW);
  Serial.flush(); 
  esp_deep_sleep_start();
  Serial.println("This will never be printed");
}


void loop() 
{
    
}
