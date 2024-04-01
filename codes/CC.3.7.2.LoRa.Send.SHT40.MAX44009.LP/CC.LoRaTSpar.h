//  CC.LoRaTSpar.h
#include <EEPROM.h>

typedef union 
{
 uint8_t buff[24]; 
 struct
  {
    uint32_t  freq;         // RT - link frequency
    uint8_t   power;        // RT - emission power
    uint8_t   sf;           // RT - link spreading factor
    uint8_t   bw;           // RT - link signal bandwidth [0:125,1:250,2:500KHz]
    uint8_t   cr;           // RT - link coding rate [0:4/5,1:4/6,2:4/7,3:4/8]
    uint8_t   aeskey[16];   // AES key
  } par;
} rtlora_t;
				// for example to be declared as rtlora_t rtlora;
typedef union 
{
 uint8_t buff[36]; 
 struct
  {
    uint32_t  channel;    // TS channel - terminal identifier
    char   wkey[16];   // write key to TS channel
    char   rkey[16];   // read key from (char *)TS channel
  } par;
} rtts_t;			// remote terminal thingspeak parameters
				
void readEEPROM(rtlora_t *lora, rtts_t *ts)
{
EEPROM.begin(512); delay(100);
for(int i=0;i<24;i++) lora->buff[i]=EEPROM.read(i);
for(int i=0;i<36;i++) ts->buff[i]=EEPROM.read(i+24);
EEPROM.end();
delay(1000);
}
