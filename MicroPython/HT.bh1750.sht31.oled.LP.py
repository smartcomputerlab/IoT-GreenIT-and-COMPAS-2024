from machine import deepsleep
import machine, time, ssd1306
from machine import Pin
from time import sleep
from bh1750 import BH1750
import sht31
from machine import SoftI2C
import esp32

def disp(p1,p2,p3):
    oled = ssd1306.SSD1306_I2C(128, 64, i2c, 0x3c)
    oled.fill(0)
    oled.text("SmartComputerLab",0,0)   # colonne 0 et ligne 0
    oled.text(p1,0,16)
    oled.text(p2,0,32)
    oled.text(p3,0,48)
    oled.show()
    sleep(5)
    oled.poweroff()

sleep(1)
print('Im starting')
sleep(1)
i2c = SoftI2C(scl=Pin(9), sda=Pin(8), freq=100000)
led = Pin (18, Pin.OUT)
bh1750 = BH1750(i2c)
while 1:
    led.value(1)
    luminosity=bh1750.luminance(BH1750.ONCE_HIRES_1)
    sensor = sht31.SHT31(i2c, addr=0x44)
    temperature,humidity=sensor.get_temp_humi()
    print("T: {:.2f}".format(temperature))
    print("H: {:.2f}".format(humidity))
    print("L: {:.2f}".format(luminosity))
    disp(str(temperature),str(humidity),str(luminosity))
    sleep(5)
    led.value(0)
    print('Im awake, but Im going to sleep')
    bh1750.off()
    deepsleep(10000) #sleep for 10 seconds


