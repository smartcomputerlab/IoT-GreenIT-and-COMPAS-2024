import machine
from machine import deepsleep,Pin,SoftI2C
import max44009
import sht21
#import esp32
import wifista
import thingspeak
from thingspeak import ThingSpeakAPI, Channel, ProtoHTTP

i2c = SoftI2C(scl=Pin(9), sda=Pin(8), freq=100000)
sensor = max44009.MAX44009(i2c)
luminosity=sensor.lux
temperature = sht21.SHT21_TEMPERATURE(i2c)
humidity = sht21.SHT21_HUMIDITE(i2c)
print("current temperature: " +str(temperature))
rtc = machine.RTC()
stfloat=0.0
r=rtc.memory()
print('woken with value',r)  # testing the last temp value
if(r!=b''):                              # skiping first empty value
    stfloat=float(r)
    print(stfloat) 

if (temperature>(stfloat+0.2) or temperature<(stfloat-0.2)):   # delta in °C ex. 0.01
    rtc.memory(str(temperature))
    print('new value to rtc memory', rtc.memory())   # test of the stored value
    channel_living_room = "1538804"
    field_temperature = "Temperature"
    field_humidity = "Humidity"
    field_luminosity = "Luminosity"
    active_channel = channel_living_room
    thing_speak = ThingSpeakAPI([
    Channel(channel_living_room , 'YOX31M0EDKO0JATK',[field_temperature, field_humidity, field_luminosity])],protocol_class=ProtoHTTP,log=True)
    wifista.connect()
    thing_speak.send(active_channel, { field_temperature: temperature, field_humidity: humidity, field_luminosity: luminosity })
    print('send to TS')
    wifista.disconnect()

deepsleep(20000)  #thing_speak.free_api_delay