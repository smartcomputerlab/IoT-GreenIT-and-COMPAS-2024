#include <WiFi.h>
#include "esp_wifi.h"
#include "ThingSpeak.h"
#include "Adafruit_SHT4x.h"
Adafruit_SHT4x sht4 = Adafruit_SHT4x();
#include "Max44009.h"
Max44009 myLux(0x4A);
char ssid[] = "PhoneAP";             // your network SSID (name)
char pass[] = "smartcomputerlab";    // your network password (use for WPA, or use as key for WEP)
unsigned long myChannelNumber =1626377;   
const char *myWriteAPIKey="3IN09682SQX3PT4Z" ;
const char *myReadAPIKey="9JVTP8ZHVTB9G4TT" ;
#define LED_PIN   18
#define uS_TO_S_FACTOR 1000000ULL   
#define TIME_TO_SLEEP  20         
RTC_DATA_ATTR float stemp=0.0,shumi=0.0,slumi=0.0; // to save last values sent

WiFiClient  client;

float temp=0.0,humi=0.0,lumi=0;
int delta=1;                   // delta*0.01 => ex: 1*0.01 => 0.01 or 1%

void readSHT41()
{
  Wire.begin(8,9);delay(10);
  if (!sht4.begin()) {   // Set to 0x45 for alternate i2c addr
        Serial.println("Couldn't find SHT41"); delay(1000);
    }
  sensors_event_t shumi, stemp;
  uint32_t timestamp = millis();
  sht4.getEvent(&shumi, &stemp);
  timestamp = millis() - timestamp;
  temp = stemp.temperature;
  humi = shumi.relative_humidity;delay(10);Serial.println();
  Serial.print("Read duration (ms): ");
  Serial.println(timestamp);
  Wire.end();
}

void readMAX44009()
{
  Wire.begin(8,9);delay(10);
  lumi = myLux.getLux();
    int err = myLux.getError();
    if (err != 0)
    {
      Serial.print("Error:\t");Serial.println(err);
    }
  Wire.end();
}

int sent_valid(float delta)      // delta value in % test of temperature only
{
  if(temp>(stemp*(1.0+delta*0.01))||temp<(stemp*(1.0-delta*0.01))) return 1;
  else return 0;
}

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
{ Serial.begin(9600);delay(100);Serial.println();
  pinMode(LED_PIN,OUTPUT);
  readSHT41();delay(10);readMAX44009();delay(10);  // reading sensors
  Serial.printf("stemp=%2.2f, shumi=%2.2f, slumi=%f\n",stemp,shumi,slumi);
  Serial.printf("temp=%2.2f, humi=%2.2f, lumi=%f\n",temp,humi,lumi);delay(10);
  if(sent_valid(1))        // sent_valid for 1*0.01 => 1%
    {
    stemp=temp;shumi=humi;slumi=lumi;   // saving sent values
    WiFi.mode(WIFI_STA); 
    WiFi.begin(ssid, pass);
    WiFi.setTxPower(WIFI_POWER_8_5dBm);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500); Serial.print(".");
    }
    Serial.println("");
    digitalWrite(LED_PIN,HIGH);
    Serial.println("Connected to WiFi");  
    ThingSpeak.begin(client); // connexion (TCP) du client au serveur
    delay(200);

    Serial.println("ThingSpeak begin");
    sdp.pay.sens[0] = temp;
    sdp.pay.sens[1] = humi;
    sdp.pay.sens[2] = lumi;
    sdp.pay.flag[0]=0xE0;sdp.pay.flag[1]=0x00;
    Serial.println("Fields update");
    if(sdp.pay.flag[0]&0x80) ThingSpeak.setField(1, sdp.pay.sens[0]);
    if(sdp.pay.flag[0]&0x40) ThingSpeak.setField(2, sdp.pay.sens[1]);
    if(sdp.pay.flag[0]&0x20) ThingSpeak.setField(3, sdp.pay.sens[2]);
    int x = ThingSpeak.writeFields(myChannelNumber, myWriteAPIKey);
    if(x == 200){Serial.println("Channel update successful.");}
    else { Serial.println("Problem updating channel. HTTP error code " + String(x));} 
    }
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32C3 to sleep for every " + String(TIME_TO_SLEEP) +" Seconds");
  Serial.println("Going to sleep now: start low_power stage");
  digitalWrite(LED_PIN,LOW);
  Serial.flush(); 
  esp_wifi_set_mode(WIFI_MODE_NULL);
  esp_deep_sleep_start();
  Serial.println("This will never be printed");
}


void loop() 
{
    
}
