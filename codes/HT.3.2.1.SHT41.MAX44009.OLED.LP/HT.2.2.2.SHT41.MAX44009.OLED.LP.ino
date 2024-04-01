#include <Wire.h>

#include "Adafruit_SHT4x.h"
Adafruit_SHT4x sht4 = Adafruit_SHT4x();

#include "Max44009.h"
Max44009 myLux(0x4A);

#include "SSD1306Wire.h"         
SSD1306Wire display(0x3c, 8, 9);    // SDA, SCL 

#define uS_TO_S_FACTOR 1000000ULL     // Conversion factor for micro seconds to seconds 
#define TIME_TO_SLEEP  10             // Time ESP32 will go to sleep (in seconds)

RTC_DATA_ATTR int bootCount = 0;

void print_wakeup_reason(){
  esp_sleep_wakeup_cause_t wakeup_reason;
  wakeup_reason = esp_sleep_get_wakeup_cause();
  switch(wakeup_reason)
  {
    case ESP_SLEEP_WAKEUP_EXT0 : Serial.println("External signal using RTC_IO"); break;
    case ESP_SLEEP_WAKEUP_EXT1 : Serial.println("External signal using RTC_CNTL"); break;
    case ESP_SLEEP_WAKEUP_TIMER : Serial.println("Wakeup caused by timer"); break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD : Serial.println("Wakeup caused by touchpad"); break;
    case ESP_SLEEP_WAKEUP_ULP : Serial.println("Wakeup caused by ULP program"); break;
    default : Serial.printf("Wakeup was not caused by deep sleep: %d\n",wakeup_reason); break;
  }
}


float temp=0.0,humi=0.0,lumi=0;

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

void display_SSD1306(float d1,float d2,float d3, int del) // del in seconds
{
  char buff1[32];char buff2[32]; 
  Wire.begin(8,9);
  display.init();
  //display.flipScreenVertically();
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.setFont(ArialMT_Plain_16);
  display.drawString(0, 0, "IoT DevKit");
  display.setFont(ArialMT_Plain_10);
  sprintf(buff1,"T: %2.2f, H: %2.2f",d1,d2);
  sprintf(buff2,"L: %5.2f",d3);
  display.drawString(0, 22, buff1);
  display.drawString(0, 36, buff2);
  display.drawString(20, 52, "SmartComputerLab");
  display.display();
  delay(del*1000);       // display during del seconds
  display.displayOff();  // disconnecting display circuit
  Wire.end();
}

void setup() 
{
  Serial.begin(9600);  // Start serial port at Baud rate
  //Increment boot number and print it every reboot
  ++bootCount;
  Serial.println("Boot number: " + String(bootCount));
  //Print the wakeup reason for ESP32
  print_wakeup_reason();
  readSHT41();
  readMAX44009();
  display_SSD1306(temp,humi,lumi,5);
  Serial.printf("temp=%2.2f, humi=%2.2f, lumi=%f\n",temp,humi,lumi);
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32 to sleep for every " + String(TIME_TO_SLEEP) +" Seconds");
  Serial.println("Going to sleep now");
  Serial.flush(); 
  esp_deep_sleep_start();

}   

void loop()
{
    Serial.println("This will never be printed");
}
