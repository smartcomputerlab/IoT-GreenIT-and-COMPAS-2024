from machine import Pin,SoftSPI
from sx127x import SX127x
from time import sleep
#import LoRaSender
import LoRaReceiveWiFiTScomp
#import LoRaPing
#import LoRaReceiverCallback
# radio – modulation parameters
lora_default = {
    'frequency': 868500000,   #869525000,
    'frequency_offset':0,
    'tx_power_level': 14,
    'signal_bandwidth': 125e3,
    'spreading_factor': 9,
    'coding_rate': 5,
    'preamble_length': 8,
    'implicitHeader': False,
    'sync_word': 0x12,
    'enable_CRC': True,
    'invert_IQ': False,
        'debug': False,
}

# pins for PYCOM-V  on SPI bus
lora_pins = {
    'dio_0':2,
    'ss':4,      # 16 on SPI-LoRa ext. card
    'reset':10,   # RST
    'sck':6,
    'miso':5,
    'mosi':7,
}

lora_spi = SoftSPI(
    baudrate=10000000, polarity=0, phase=0,
    bits=8, firstbit=SoftSPI.MSB,
    sck=Pin(lora_pins['sck'], Pin.OUT, Pin.PULL_DOWN),
    mosi=Pin(lora_pins['mosi'], Pin.OUT, Pin.PULL_UP),
    miso=Pin(lora_pins['miso'], Pin.IN, Pin.PULL_UP),
)

lora = SX127x(lora_spi, pins=lora_pins, parameters=lora_default)

# type = 'sender'
# type = 'receiver'
# type = 'ping_master'
# type = 'ping_slave'
# type = 'receiver_callback'
# type = 'receiver_gateway'

type = 'receiver_gateway'     # let us select sender method

if __name__ == '__main__':
    if type == 'sender':
        LoRaSender.send(lora)
    if type == 'receiver':
        LoRaReceiver.receive(lora)
    if type == 'ping_master':
        LoRaPing.ping(lora, master=True)
    if type == 'receiver_gateway':
        LoRaReceiveWiFiTScomp.receive(lora)
    if type == 'receiver_callback':
        LoRaReceiverCallback.receiveCallback(lora)
        
  
  
  
