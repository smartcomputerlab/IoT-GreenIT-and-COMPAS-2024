#
# Librairie permettant de gerer le capteur de temperature
# et d'humidite SHT21 / HTU21
# Tester sur NodeMCU Lolin
#
# Auteur : iTechnoFrance
#

from machine import I2C, Pin
import time

_address_sht21 = 0x40 # adresse du capteur SHT21 sur le bus I2C
_soft_reset_sht21 = b'\xFE' # commande pour effectuer un reboot
_lecture_temperature_sht21 = b'\xF3' # commande pour temperature NO HOLD MASTER MODE
_lecture_humidite_sht21 = b'\xF5' # commande pour humidite NO HOLD MASTER MODE
_lecture_registre_sht21 = b'\xE7' # commande pour lire le registre utilisateur
_ecriture_registre_sht21 = b'\xE6' # commande pour ecrire le registre utilisateur

# teste la presence du capteur SH21
def SHT21_DETECT(_i2c):
    _is_present = False
    _i2c_peripheriques = _i2c.scan()
    for _i2c_peripherique in _i2c_peripheriques:    
      if (_i2c_peripherique == _address_sht21):
        _is_present = True
    return _is_present

# initialise un reboot du capteur
def SHT21_RESET(_i2c):
    _response = False
    _ack = _i2c.writeto(_address_sht21, _soft_reset_sht21)
    time.sleep(0.015) # delai 15ms pour effectuer le reboot
    if (_ack == 1):
        _response = True
    return _response 

# recupere le numero de serie du capteur
def SHT21_SERIAL(_i2c):
    _serial_number_sht21 = bytearray(8) # 8 octets pour le numero de serie
    _data_sht21_1 = bytearray(8) # 8 octets a lire pour l'acces memoire 1
    _data_sht21_2 = bytearray(6) # 6 octets a lire pour l'acces memoire 2
    _i2c.writeto(_address_sht21, b'\xFA\x0F') # acces memoire 1 pour le numero de serie
    _i2c.readfrom_into(_address_sht21, _data_sht21_1)
    _i2c.writeto(_address_sht21, b'\xFC\xC9') # acces memoire 2 pour le numero de serie
    _i2c.readfrom_into(_address_sht21, _data_sht21_2)
    _serial_number_sht21[0] = _data_sht21_2[3] # SNA1
    _serial_number_sht21[1] = _data_sht21_2[4] # SNA0
    _serial_number_sht21[2] = _data_sht21_1[0] # SNB3
    _serial_number_sht21[3] = _data_sht21_1[2] # SNB2
    _serial_number_sht21[4] = _data_sht21_1[4] # SNB1
    _serial_number_sht21[5] = _data_sht21_1[6] # SNB0
    _serial_number_sht21[6] = _data_sht21_2[0] # SNC1
    _serial_number_sht21[7] = _data_sht21_2[1] # SNC0
    return "".join("%02x" % b for b in _serial_number_sht21) # retourne un String du numero de serie

# recupere la temperature    
def SHT21_TEMPERATURE(_i2c):
    # la temperature en Celsius est obtenue avec la formule suivante
    # T = -46.85 + 175.72 * (mesure / 2 puissance 16)
    # ou mesure est la valeur fournie par le capteur
    _mesure_temperature_sht21 = bytearray(3) # 3 octets pour la mesure de temperature + 1 octet pour CRC
    _i2c.writeto(_address_sht21, _lecture_temperature_sht21)
    time.sleep(0.085) # delai de 85ms pour la mesure de temperature avec resolution 14 bits par defaut
    _i2c.readfrom_into(_address_sht21, _mesure_temperature_sht21)
    # _mesure_temperature_sht21[1] & ~0x0003 : efface les 2 derniers bits, qui indiquent le type de mesure temp ou humidite
    _temperature_sht21 = (_mesure_temperature_sht21[0] << 8) + (_mesure_temperature_sht21[1] & ~0x0003)
    _temperature_sht21 *= 175.72
    _temperature_sht21 /= 1 << 16 # divise par 2 puissance 16
    _temperature_sht21 -= 46.85
    if SHT21_CRC(_mesure_temperature_sht21, 2) == _mesure_temperature_sht21[2]:
        return _temperature_sht21
    else:
        return -1

# recupere l'humidite relative    
def SHT21_HUMIDITE(_i2c):
    # l'humidite relative en % est obtenue avec la formule suivante
    # RH = -6 + (125 * (mesure / 2 ^16))
    # ou mesure est la valeur fournie par le capteur
    _mesure_humidite_sht21 = bytearray(3) # 2 octets pour la mesure d'humidite + 1 octet pour CRC
    _i2c.writeto(_address_sht21, _lecture_humidite_sht21)
    time.sleep(0.029) # delai de 29ms pour la mesure d'humidite avec resolution 12 bits par defaut
    _i2c.readfrom_into(_address_sht21, _mesure_humidite_sht21)
    # _mesure_humidite_sht21[1] & ~0x0003 : efface les 2 derniers bits, qui indiquent le type de mesure temp ou humidite
    _humidite_sht21 = (_mesure_humidite_sht21[0] << 8) + (_mesure_humidite_sht21[1] & ~0x0003)
    _humidite_sht21 *= 125
    _humidite_sht21 /= 1 << 16 # divise par 2 puissance 16
    _humidite_sht21 -= 6
    if SHT21_CRC(_mesure_humidite_sht21, 2) == _mesure_humidite_sht21[2]:
        return _humidite_sht21
    else:
        return -1

# calcul le CRC
def SHT21_CRC(donnees, nbr_octets):
    crc = 0
    POLYNOMIAL = 0x131  # P(x)=x^8+x^5+x^4+1 = 100110001 fournit par la documentation du capteur
    for octet in range(nbr_octets):
        crc ^= donnees[octet] # XOR
        for bit in range(8, 0, -1):
            if (crc & 0x80):
                crc = (crc << 1) ^ POLYNOMIAL
            else:
                crc = (crc << 1)
    return crc

# Verifie l'alimentation du capteur
def SHT21_ALIMENTATION(_i2c):
    # permet de verifier si l'alimentation du module est ok : > 2.25v
    registre_sht21 = bytearray(1) # 1 octet pour le registre
    _i2c.writeto(_address_sht21, _lecture_registre_sht21)
    _i2c.readfrom_into(_address_sht21, registre_sht21)
    registre_sht21[0] &= 0x40 # recupere le bit 6
    if (registre_sht21[0] == 0x40):
        return False # alimentation < 2.25v
    else:
        return True # alimentation > 2.25v

# recupere la resolution des mesures temperature et humidite        
def SHT21_GET_RESOLUTION(_i2c):
    # recupere la resolution de la mesure Humidite et Temperature
    _registre_sht21 = bytearray(1) # 1 octet pour le registre
    _i2c.writeto(_address_sht21, _lecture_registre_sht21)
    _i2c.readfrom_into(_address_sht21, _registre_sht21)
    _registre_sht21[0] &= 0x81 # recupere le bit 7 et le bit 0
    if (_registre_sht21[0] == 0):
        return "H:12 T:14 bits"
    if (_registre_sht21[0] == 1):
        return "H:8 T:12 bits"
    if (_registre_sht21[0] == 0x80):
        return "H:10 T:13 bits"
    if (_registre_sht21[0] == 0x81):
        return "H:11 T:11 bits"

# permet de definir la resolution a utiliser pour les mesures
def SHT21_SET_RESOLUTION(_i2c, _choix_resolution_sht21):
    # definit la resolution de la mesure Humidite et Temperature
    _registre_sht21 = bytearray(1) # 1 octet pour lire le registre
    _resolution_sht21 = bytearray(2) # 2 octets pour ecrire le registre
    _resolution_sht21[0] = _ecriture_registre_sht21[0] 
    _i2c.writeto(_address_sht21, _lecture_registre_sht21)
    _i2c.readfrom_into(_address_sht21, _registre_sht21)
    if (_choix_resolution_sht21 == 0): # resolution RH: 12 bits T: 14 bits
        _resolution_sht21[1] = _registre_sht21[0] & 0x7E # bit 7 et bit 0 a 0
        _i2c.writeto(_address_sht21, _resolution_sht21)
    if (_choix_resolution_sht21 == 1): # resolution RH: 8 bits T: 12 bits
        _resolution_sht21[1] = _registre_sht21[0] & 0x7F | 0x01 # bit 7 a 0 et bit 0 a 1
        _i2c.writeto(_address_sht21, _resolution_sht21)
    if (_choix_resolution_sht21 == 2): # resolution RH: 10 bits T: 13 bits
        _resolution_sht21[1] = _registre_sht21[0] & 0xFE | 0x80 # bit 7 a 1 et bit 0 a 0
        _i2c.writeto(_address_sht21, _resolution_sht21)
    if (_choix_resolution_sht21 == 3): # resolution RH: 11 bits T: 11 bits
        _resolution_sht21[1] = _registre_sht21[0] | 0x81 # bit 7 a 1 et bit 0 a 1
        _i2c.writeto(_address_sht21, _resolution_sht21)