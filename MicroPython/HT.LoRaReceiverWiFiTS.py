from time import sleep
import machine, ssd1306
from machine import Pin, SoftI2C
import esp32,time
import ustruct
import wifista
import thingspeak
from thingspeak import ThingSpeakAPI, Channel, ProtoHTTP

def disp(t,h,l,r):
    i2c = SoftI2C(scl=Pin(9), sda=Pin(8), freq=100000)
    oled = ssd1306.SSD1306_I2C(128, 64, i2c, 0x3c)
    oled.fill(0)
    oled.text("SmartComputerLab", 0, 0)
    oled.text(str(t), 0, 18)
    oled.text(str(h), 0, 30)
    oled.text(str(l), 0, 42)
    oled.text(str(r), 0, 54)
    oled.show()
    #sleep(5)
    #oled.poweroff()

def receive(lora):
    print("LoRa Receiver and WiFi Gateway")
    wifista.connect()
    channel_living_room = "1538804"
    active_channel = channel_living_room
    field_temperature = "Temperature"
    field_humidity = "Humidity"
    field_luminosity = "Luminosity"
    field_rssi = "RSSI"
    thing_speak = ThingSpeakAPI([
    Channel(channel_living_room , 'YOX31M0EDKO0JATK', [field_temperature, field_humidity, field_luminosity, field_rssi])],
    protocol_class=ProtoHTTP, log=True)
    print("LoRa Receiver - witing for packet")
    while True:
        if lora.receivedPacket():
            try:
                data = lora.readPayload()
                rssi = float(lora.packetRssi())
                chan,wkey,temp,humi,lumi,count=ustruct.unpack('i16s4f',data)
                print("channel: " + str(chan))
                print("wkey: " + str(wkey))
                print("temp: " + str(temp))
                print("humi: " + str(humi))
                print("lumi: " + str(lumi))
                print("count: " + str(count))
                print("rssi: " + str(rssi))
                #print("data: {}".format(data))
                disp(temp,humi,lumi,rssi)
                thing_speak.send(active_channel, {
                        field_temperature: temp,
                        field_humidity: humi,
                        field_luminosity: lumi,
                        field_rssi: rssi
                        })
                print('send to TS')
                time.sleep(thing_speak.free_api_delay)
            except Exception as e:
                print(e)
