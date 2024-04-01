#define LED_PIN   18
#define uS_TO_S_FACTOR 1000000ULL  /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP  10        /* Time ESP32 will go to sleep (in seconds) */
RTC_DATA_ATTR int bootCount = 0;


void setup(){
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN,HIGH);Serial.println();
  Serial.println("Starting high_power stage: processing phase - 5 seconds");
  delay(5000); // operational time
  ++bootCount;
  Serial.println("Boot number: " + String(bootCount));
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32C3 to sleep for every " + String(TIME_TO_SLEEP) +" Seconds");
  Serial.println("Going to sleep now: start low_power stage");
  digitalWrite(LED_PIN,LOW);
  Serial.flush(); 
  esp_deep_sleep_start();
  Serial.println("This will never be printed");
}

void loop(){
  //This is not going to be called
}
