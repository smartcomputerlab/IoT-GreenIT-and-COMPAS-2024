from machine import Pin

def scan():
    import network
    station = network.WLAN(network.STA_IF)
    station.active(True)

    for (ssid, bssid, channel, RSSI, authmode, hidden) in station.scan():
        print("* {:s}".format(ssid))
        print(" - Channel: {}".format(channel))
        print(" - RSSI: {}".format(RSSI))
        print(" - BSSID: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}".format(*bssid))
        print()


def connect():
    import network
    ip       = '192.168.1.110'
    subnet    = '255.255.255.0'
    gateway   = '192.168.1.1'
    dns       = '8.8.8.8'

    ssid      = "Livebox-08B0"
    password  =  "G79ji6dtEptVTPWmZP"
    ssid2      = "PhoneAP"
    password2  =  "smartcomputerlab"
    
    station = network.WLAN(network.STA_IF)
    
    if station.isconnected() == True:
        print("Already connected")
        return station
 
    station.active(True)
    station.connect(ssid,password)
    station.config(txpower=8.5)
    while station.isconnected() == False:
        pass
    print("Connection successful")
    print(station.ifconfig())
    return station

def disconnect():
    import network
    station = network.WLAN(network.STA_IF)
    station.disconnect()
    station.active(False)
    

scan()
disconnect()
connect()
 