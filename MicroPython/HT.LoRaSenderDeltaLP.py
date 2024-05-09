# LoRaSenderDeltaLP.py

from time import sleep
import machine, ssd1306
from machine import Pin, SoftI2C
import max44009
import sht21
import ustruct

def disp(t,h,l):
    i2c = SoftI2C(scl=Pin(9), sda=Pin(8), freq=100000)
    oled = ssd1306.SSD1306_I2C(128, 64, i2c, 0x3c)
    oled.fill(0)
    oled.text("SmartComputerLab", 0, 0)
    oled.text(str(t), 0, 16)
    oled.text(str(h), 0, 32)
    oled.text(str(l), 0, 48)
    oled.show()
    sleep(5)
    oled.poweroff()

def send(lora):
    i2c = SoftI2C(scl=Pin(9), sda=Pin(8), freq=100000)
    rtc = machine.RTC()
    stfloat=0.0
    r=rtc.memory()
    print('woken with value',r)  # testing the last temp value
    if(r!=b''):                              # skiping first empty value
        stfloat=float(r)
        print(stfloat)                      # formatting float for stored temperature
        
    chan =12345
    wkey="abcdefghijklmnop"    
    lumsensor = max44009.MAX44009(i2c)
    luminosity=lumsensor.lux
    temperature = sht21.SHT21_TEMPERATURE(i2c)
    humidity = sht21.SHT21_HUMIDITE(i2c)
    
    if (temperature>(stfloat+0.01) or temperature<(stfloat-0.01)):
        led = Pin (18, Pin.OUT)
        led.value(1)
        rtc.memory(str(temperature))
        print('new value to rtc memory', rtc.memory())   # test of the stored value
        print("LoRa Sender")
        counter=0.0             
        """ test lines
        print(data)
        print("datalen: " + str(len(data)))
        chan,wkey,temp,humi,lumi,count=ustruct.unpack('i16s4f',data)
        print("chan "+str(chan))
        print("wkey "+ str(wkey))
        print("temp "+str(temp))
        print("humi "+ str(humi))
        print("C: {:d}".format(chan))
        print("S: {:16s}".format(wkey))
        print("T: {:.2f}".format(temp))
        print("H: {:.2f}".format(humi))
        print("L: {:.2f}".format(lumi))
        """
        data=ustruct.pack('i16s4f',chan,wkey,temperature,humidity,luminosity,counter)
        print("datalen: " + str(len(data)))
        lora.beginPacket()
        lora.write(data)
        lora.endPacket()
        sleep(1)
        led.value(0)
        disp(temperature,humidity,luminosity)


