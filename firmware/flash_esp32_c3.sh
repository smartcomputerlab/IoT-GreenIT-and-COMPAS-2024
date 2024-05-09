esptool.py --chip esp32c3 --port /dev/ttyACM1 erase_flash #--flash_mode dio 
#esptool.py --chip esp32c3 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32c3 --port /dev/ttyACM1 --baud 460800 write_flash -z 0x0 $1
#esptool.py --chip esp32c3 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x0 $1



