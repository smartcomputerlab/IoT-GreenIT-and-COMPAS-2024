
#include <SPI.h>               
#include <LoRa.h>
#include <Wire.h> 
#include "Adafruit_SHT4x.h"
Adafruit_SHT4x sht4 = Adafruit_SHT4x();
#include "Max44009.h"
Max44009 myLux(0x4A);



#define uS_TO_S_FACTOR 1000000ULL     // Conversion factor for micro seconds to seconds 
#define TIME_TO_SLEEP  10             // Time ESP32 will go to sleep (in seconds)

RTC_DATA_ATTR float stemp=0.0,shumi=0.0,slumi=0.0; // to save last values sent
RTC_DATA_ATTR uint32_t count=0;

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
} rt_lora_t;
rt_lora_t rtlora;

unsigned long myChannelNumber =1626377;   
const char *myWriteAPIKey="3IN09682SQX3PT4Z" ;
const char *myReadAPIKey="9JVTP8ZHVTB9G4TT" ;

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



void setLoRaPar()         // set LoRa radio parameters
{
  rtlora.par.freq= 434E6; //868E6;
  rtlora.par.sf= 7;
  rtlora.par.bw= 125E3;
  rtlora.par.cr=5;
}

float temp=0.0,humi=0.0,lumi=0.0;

void readSHT41(float *tem, float *hum)
{
  Wire.begin(8,9);delay(10);
  if (!sht4.begin()) {   // Set to 0x45 for alternate i2c addr
        Serial.println("Couldn't find SHT41"); delay(1000);
    }
  sensors_event_t ehumi, etemp;
  uint32_t timestamp = millis();
  sht4.getEvent(&ehumi, &etemp);
  timestamp = millis() - timestamp;
  *tem = (float)etemp.temperature;
  *hum = (float)ehumi.relative_humidity;delay(10);Serial.println();
  Serial.print("Read duration (ms): ");
  Serial.println(timestamp);delay(20);
  Wire.end();delay(10);
}
void readMAX44009(float *lux)
{
  Wire.begin(8,9);delay(10);
  *lux = (float)myLux.getLux();
    int err = myLux.getError();
    if (err != 0)
    {
      Serial.print("Error:\t");Serial.println(err);
    }
  delay(20);
  Wire.end();delay(10);
}

int sent_valid(float delta)      // delta value in % test of temperature only
{
  if(temp>(stemp*(1.0+delta*0.01))||temp<(stemp*(1.0-delta*0.01))) return 1;
  else return 0;
}

void setup() 
{
pack_t sdp; 
  float ntemp,nhumi,nlumi,lux;
  Serial.begin(9600); Serial.println();
  readSHT41(&ntemp,&nhumi);
  readMAX44009(&nlumi); 
  sdp.pay.sens1=22.22; //ntemp; 
  sdp.pay.sens2=44.44; //nhumi;
  sdp.pay.sens3=1235.4; //nlumi;
  sdp.pay.channel=myChannelNumber;
  strncpy(sdp.pay.wkey,myWriteAPIKey,16);
  sdp.pay.flag[0]=0xE0;sdp.pay.flag[1]=0x00; 
  sdp.pay.number=count; count++;
  Serial.printf("temp:%2.2f,humi:%2.2f,lumi=%6.2f, count=%d\n",ntemp,nhumi,nlumi,count);
    delay(10);          
    SPI.begin(SCK,MISO,MOSI,SS);
    LoRa.setPins(SS,RST,DI0);
    setLoRaPar();
    Serial.println();delay(100);Serial.println();
    Serial.printf("LoRa freq: %d\n",rtlora.par.freq);
    Serial.printf("LoRa sf: %d\n",rtlora.par.sf);
    Serial.printf("LoRa bw: %d\n",rtlora.par.bw);
    Serial.printf("LoRa cr: %d\n",rtlora.par.cr);
    if (!LoRa.begin(rtlora.par.freq)) {
      Serial.println("Starting LoRa failed!");
      while (1);}
    Serial.println("Starting LoRa OK!");delay(10);
    LoRa.setSpreadingFactor(rtlora.par.sf);
    LoRa.setSignalBandwidth(rtlora.par.bw);
    LoRa.setCodingRate4(rtlora.par.cr);
    if(!(count%5))
      {
      Serial.println("New Packet") ;
      LoRa.beginPacket(); // start packet
      LoRa.write((uint8_t *)sdp.frame,58);
      LoRa.endPacket();
      Serial.flush(); 
      }
    delay(10);
    LoRa.end();delay(10);
    SPI.end();delay(10);
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32 to sleep for every " + String(TIME_TO_SLEEP) +" Seconds");
  Serial.println("Going to sleep now");
  esp_deep_sleep_start();
}

void loop()
{ }
