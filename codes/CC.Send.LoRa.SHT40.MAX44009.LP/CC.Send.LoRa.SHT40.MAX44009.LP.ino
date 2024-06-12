#include "LoRaWan_APP.h"
#include "Arduino.h"
#include <Wire.h> 
#include "Adafruit_SHT4x.h"
Adafruit_SHT4x sht4 = Adafruit_SHT4x();
#include "Max44009.h"
Max44009 myLux(0x4A);

#ifndef LoraWan_RGB
#define LoraWan_RGB 0
#endif
#define RX_TIMEOUT_VALUE 1000
static RadioEvents_t RadioEvents;
float txNumber;
bool lora_idle=true;

unsigned long myChannelNumber =1626377;   
const char *myWriteAPIKey="3IN09682SQX3PT4Z" ;
const char *myReadAPIKey="9JVTP8ZHVTB9G4TT" ;

TimerEvent_t sleepTimer;
//Records whether our sleep/low power timer expired
bool sleepTimerExpired;

static void wakeUp()
{
  sleepTimerExpired=true;
}

static void lowPowerSleep(uint32_t sleeptime)
{
  sleepTimerExpired=false;
  TimerInit( &sleepTimer, &wakeUp );
  TimerSetValue( &sleepTimer, sleeptime );
  TimerStart( &sleepTimer );
  while (!sleepTimerExpired) lowPowerHandler();
  TimerStop( &sleepTimer );
  }

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
 
typedef union 
{
 uint8_t frame[36]; 
 struct
  {
   uint32_t    channel;
   char        wkey[16];
   float       sens[4]; 
  } pay;
} pack_t;
pack_t sdp; // packet to send

void setLoRaPar()         // set LoRa radio parameters
{
  rtlora.par.freq= 868E6;
  rtlora.par.power= 14;
  rtlora.par.sf= 7;
  rtlora.par.bw= 0;   // [0:125KHz,1:250KHz,2:500KHz]
  rtlora.par.cr=1;    // [1:4/5,2:4/6,3:4/7,4:4/8]
}

static uint16_t counter=0;
static float stemp=0.0,shumi=0.0,slumi=0.0;

uint16_t read_Bat()
{
uint16_t v;
  delay(40);
  pinMode(VBAT_ADC_CTL,OUTPUT);delay(40);
  digitalWrite(VBAT_ADC_CTL,LOW);delay(40);
  v=analogRead(ADC)+550; // some callibration
  pinMode(VBAT_ADC_CTL, INPUT);
  return v;
}

float temp=0.0,humi=0.0,lumi=0.0;

void readSHT41(float *tem, float *hum)
{
  pinMode(Vext,OUTPUT);
  digitalWrite(Vext,LOW); delay(100);
  Wire.begin();
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
  digitalWrite(Vext,HIGH); delay(20);Wire.end();
}

void readMAX44009(float *lux)
{
  pinMode(Vext,OUTPUT);
  digitalWrite(Vext,LOW); delay(100);
  Wire.begin();delay(20);
  *lux = (float)myLux.getLux();
    int err = myLux.getError();
    if (err != 0)
    {
      Serial.print("Error:\t");Serial.println(err);
    }
  delay(20);
  Wire.end();delay(10);
  digitalWrite(Vext,HIGH); delay(20);Wire.end();
}

int sent_valid(float s_sens, float sens, float delta)      // delta value in % test of temperature only
{
  if(sens>(s_sens*(1.0+delta*0.01))||sens<(s_sens*(1.0-delta*0.01))) return 1;
  else return 0;
}

void setup(){
  Serial.begin(9600);delay(300);
  setLoRaPar();                            // read lora parameters and TS parameters
  Serial.printf("Frequency:%d\n",rtlora.par.freq);
  Serial.printf("Trans power:%d\n",rtlora.par.power);
  Serial.printf("Bandwidth [0:125KHz,1:250KHz,2:500KHz, ]: %d\n",rtlora.par.bw);
  Serial.printf("Spreading factor: %d\n",rtlora.par.sf);
  Serial.printf("Code rate [1:4/5,2:4/6,3:4/7,4:4/8]: %d\n",rtlora.par.cr);
  txNumber=0;
  RadioEvents.TxDone = OnTxDone;RadioEvents.TxTimeout = OnTxTimeout;
  Radio.Init( &RadioEvents );
  Radio.SetChannel(rtlora.par.freq);
  Radio.SetTxConfig( MODEM_LORA, rtlora.par.power, 0, rtlora.par.bw,
        rtlora.par.sf, rtlora.par.cr, 8, false,
        true, 0, 0, false, 3000 ); 
}


static int ttsleep=10000;

void loop()
{ 
  turnOffRGB();counter++; digitalWrite(Vext,HIGH);
  Serial.printf("\ntime_to_sleep=%d ms\n", ttsleep);delay(100);
  lowPowerSleep(ttsleep); // lora_idle = true;
  Serial.printf("\nBack from sleep %d, counter=%d\n", millis(),counter);
  float ntemp,nhumi,nlumi,lux;
  readSHT41(&ntemp,&nhumi);
  readMAX44009(&nlumi);
  if(sent_valid(stemp,ntemp,0.1))
    {
    if(lora_idle == true)  // is true when TX is done !
      {
      stemp=ntemp;shumi=nhumi;slumi=nlumi;  
      sdp.pay.channel=myChannelNumber;
      strncpy(sdp.pay.wkey,myWriteAPIKey,16);
      Serial.printf("\nChannel - ID: %d\n",myChannelNumber);
      Serial.printf("Channel write key: %16.16s\n",myWriteAPIKey);
      sdp.pay.sens[0]=ntemp; sdp.pay.sens[1]=nhumi;
      sdp.pay.sens[2]=nlumi; sdp.pay.sens[3]=(int)read_Bat();
      Serial.printf("Field_1:%2.2f, Field_2:%2.2f \n",sdp.pay.sens[0],sdp.pay.sens[1]);
      Serial.printf("Field_3:%2.2f, Field_4:%2.2f \n",sdp.pay.sens[2],sdp.pay.sens[3]);
      Radio.Send( (uint8_t *)sdp.frame,36 ); //send the package out 
      lora_idle = false; Serial.println();digitalWrite(Vext, HIGH); delay(100); 
      turnOnRGB(COLOR_SEND,0);counter++;delay(100);
      }
  }
}

void OnTxDone( void )
{
  turnOffRGB();Radio.Sleep(); // Radio.Sleep() to stop the modem until the next transmission
  Serial.println("TX done......");delay(10);
  lora_idle = true;
}

void OnTxTimeout( void )
{
  turnOffRGB();
  Radio.Sleep( ); Serial.println("TX Timeout......");
  lora_idle = true;
}
