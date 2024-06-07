from time import sleep, ticks_ms
from machine import SPI, Pin
from micropython import const
import gc


PA_OUTPUT_RFO_PIN = const(0)
PA_OUTPUT_PA_BOOST_PIN = const(1)

# registers
REG_FIFO = const(0x00)
REG_OP_MODE = const(0x01)
REG_FRF_MSB = const(0x06)
REG_FRF_MID = const(0x07)
REG_FRF_LSB = const(0x08)
REG_PA_CONFIG = const(0x09)
REG_LNA = const(0x0C)
REG_FIFO_ADDR_PTR = const(0x0D)

REG_FIFO_TX_BASE_ADDR = const(0x0E)
FifoTxBaseAddr = const(0x00)

REG_FIFO_RX_BASE_ADDR = const(0x0F)
FifoRxBaseAddr = const(0x00)
REG_FIFO_RX_CURRENT_ADDR = const(0x10)
REG_IRQ_FLAGS_MASK = const(0x11)
REG_IRQ_FLAGS = const(0x12)
REG_RX_NB_BYTES = const(0x13)
REG_PKT_RSSI_VALUE = const(0x1A)
REG_PKT_SNR_VALUE = const(0x19)
REG_MODEM_CONFIG_1 = const(0x1D)
REG_MODEM_CONFIG_2 = const(0x1E)
REG_PREAMBLE_MSB = const(0x20)
REG_PREAMBLE_LSB = const(0x21)
REG_PAYLOAD_LENGTH = const(0x22)
REG_FIFO_RX_BYTE_ADDR = const(0x25)
REG_MODEM_CONFIG_3 = const(0x26)
REG_RSSI_WIDEBAND = const(0x2C)
REG_DETECTION_OPTIMIZE = const(0x31)
REG_DETECTION_THRESHOLD = const(0x37)
REG_SYNC_WORD = const(0x39)
REG_DIO_MAPPING_1 = const(0x40)
REG_VERSION = const(0x42)

# invert IQ
REG_INVERTIQ = const(0x33)
RFLR_INVERTIQ_RX_MASK = const(0xBF)
RFLR_INVERTIQ_RX_OFF = const(0x00)
RFLR_INVERTIQ_RX_ON = const(0x40)
RFLR_INVERTIQ_TX_MASK = const(0xFE)
RFLR_INVERTIQ_TX_OFF = const(0x01)
RFLR_INVERTIQ_TX_ON = const(0x00)

REG_INVERTIQ2 = const(0x3B)
RFLR_INVERTIQ2_ON = const(0x19)
RFLR_INVERTIQ2_OFF = const(0x1D)

# modes
# bit 7: 1 => LoRa mode
MODE_LONG_RANGE_MODE = const(0x80)
MODE_SLEEP = const(0x00)
MODE_STDBY = const(0x01)
MODE_TX = const(0x03)
MODE_RX_CONTINUOUS = const(0x05)
MODE_RX_SINGLE = const(0x06)

# PA config
PA_BOOST = const(0x80)

# IRQ masks
IRQ_TX_DONE_MASK = const(0x08)
IRQ_PAYLOAD_CRC_ERROR_MASK = const(0x20)
IRQ_RX_DONE_MASK = const(0x40)
IRQ_RX_TIME_OUT_MASK = const(0x80)

# Buffer size
MAX_PKT_LENGTH = const(255)


class SX127x:

    default_parameters = {
        "frequency": 869525000,
        "frequency_offset": 0,
        "tx_power_level": 14,
        "signal_bandwidth": 125e3,
        "spreading_factor": 9,
        "coding_rate": 5,
        "preamble_length": 8,
        "implicitHeader": False,
        "sync_word": 0x12,
        "enable_CRC": True,
        "invert_IQ": False,
    }

    def __init__(self, spi, pins, parameters={}):
        self.spi = spi
        self.pins = pins
        self.parameters = parameters

        self.pin_ss = Pin(self.pins["ss"], Pin.OUT)

        self.lock = False
        self.implicit_header_mode = None

        self.parameters = SX127x.default_parameters
        if parameters:
            self.parameters.update(parameters)

        # check version
        version = None
        for i in range(5):
            version = self.readRegister(REG_VERSION)
            if version:
                break
        # debug output
        print("SX version: {}".format(version))

        # put in LoRa and sleep mode
        self.sleep()
        # config
        self.setFrequency(self.parameters["frequency"])
        self.setSignalBandwidth(self.parameters["signal_bandwidth"])

        # set LNA boost
        self.writeRegister(REG_LNA, self.readRegister(REG_LNA) | 0x03)
        # set auto AGC
        self.writeRegister(REG_MODEM_CONFIG_3, 0x04)

        self.setTxPower(self.parameters["tx_power_level"])
        self.implicitHeaderMode(self.parameters["implicitHeader"])
        self.setSpreadingFactor(self.parameters["spreading_factor"])
        self.setCodingRate(self.parameters["coding_rate"])
        self.setPreambleLength(self.parameters["preamble_length"])
        self.setSyncWord(self.parameters["sync_word"])
        self.enableCRC(self.parameters["enable_CRC"])
        self.invertIQ(self.parameters["invert_IQ"])

        # set LowDataRateOptimize flag if symbol time > 16ms (default disable on reset)
        # self.writeRegister(REG_MODEM_CONFIG_3, self.readRegister(REG_MODEM_CONFIG_3) & 0xF7)  # default disable on reset
        bw = self.parameters["signal_bandwidth"]
        sf = self.parameters["spreading_factor"]
        if 1000 / bw / 2 ** sf > 16:
            self.writeRegister(
                REG_MODEM_CONFIG_3, self.readRegister(REG_MODEM_CONFIG_3) | 0x08
            )

        # set base addresses
        self.writeRegister(REG_FIFO_TX_BASE_ADDR, FifoTxBaseAddr)
        self.writeRegister(REG_FIFO_RX_BASE_ADDR, FifoRxBaseAddr)

        self.standby()

    def beginPacket(self, implicitHeaderMode=False):
        self.standby()
        self.implicitHeaderMode(implicitHeaderMode)

        # reset FIFO address and payload length
        self.writeRegister(REG_FIFO_ADDR_PTR, FifoTxBaseAddr)
        self.writeRegister(REG_PAYLOAD_LENGTH, 0)

    def endPacket(self):
        # put in TX mode
        self.writeRegister(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_TX)
        # wait for TX done, standby automatically on TX_DONE
        while (self.readRegister(REG_IRQ_FLAGS) & IRQ_TX_DONE_MASK) == 0:
            pass
        # clear IRQ's
        self.writeRegister(REG_IRQ_FLAGS, IRQ_TX_DONE_MASK)

    def write(self, buffer):
        currentLength = self.readRegister(REG_PAYLOAD_LENGTH)
        size = len(buffer)

        # check size
        size = min(size, (MAX_PKT_LENGTH - FifoTxBaseAddr - currentLength))

        # write data
        for i in range(size):
            self.writeRegister(REG_FIFO, buffer[i])

        # update length
        self.writeRegister(REG_PAYLOAD_LENGTH, currentLength + size)
        return size

    def aquirelock(self, lock=False):
        self.lock = False

    def println(self, message, implicitHeader=False, repeat=1):
        # wait until RX_Done, lock and begin writing
        self.aquirelock(True)

        if isinstance(message, str):
            message = message.encode()

        self.beginPacket(implicitHeader)
        self.write(message)

        for i in range(repeat):
            self.endPacket()

        # unlock when done writing
        self.aquirelock(False)
        self.collectGarbage()

    def getIrqFlags(self):
        irqFlags = self.readRegister(REG_IRQ_FLAGS)
        self.writeRegister(REG_IRQ_FLAGS, irqFlags)
        return irqFlags

    def packetRssi(self, rfi="hf"):
        packet_rssi = self.readRegister(REG_PKT_RSSI_VALUE)
        return packet_rssi - (157 if rfi == "hf" else 164)

    def packetSnr(self):
        return (self.readRegister(REG_PKT_SNR_VALUE)) * 0.25

    def standby(self):
        self.writeRegister(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STDBY)

    def sleep(self):
        self.writeRegister(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_SLEEP)

    def setTxPower(self, level, outputPin=PA_OUTPUT_PA_BOOST_PIN):
        self.parameters["tx_power_level"] = level
        if outputPin == PA_OUTPUT_RFO_PIN:
            # RFO
            level = min(max(level, 0), 14)
            self.writeRegister(REG_PA_CONFIG, 0x70 | level)
        else:
            # PA BOOST
            level = min(max(level, 2), 17)
            self.writeRegister(REG_PA_CONFIG, PA_BOOST | (level - 2))

    def setFrequency(self, frequency):
        # TODO min max limit
        frequency = int(frequency)
        self.parameters["frequency"] = frequency
        frequency += self.parameters["frequency_offset"]

        frf = (frequency << 19) // 32000000
        self.writeRegister(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self.writeRegister(REG_FRF_MID, (frf >> 8) & 0xFF)
        self.writeRegister(REG_FRF_LSB, (frf >> 0) & 0xFF)

    def setSpreadingFactor(self, sf):
        sf = min(max(sf, 6), 12)
        self.writeRegister(REG_DETECTION_OPTIMIZE, 0xC5 if sf == 6 else 0xC3)
        self.writeRegister(REG_DETECTION_THRESHOLD, 0x0C if sf == 6 else 0x0A)
        self.writeRegister(
            REG_MODEM_CONFIG_2,
            (self.readRegister(REG_MODEM_CONFIG_2) & 0x0F) | ((sf << 4) & 0xF0),
        )

    def setSignalBandwidth(self, sbw):
        bins = (
            7.8e3,
            10.4e3,
            15.6e3,
            20.8e3,
            31.25e3,
            41.7e3,
            62.5e3,
            125e3,
            250e3,
        )
        bw = 9

        if sbw < 10:
            bw = sbw
        else:
            for i in range(len(bins)):
                if sbw <= bins[i]:
                    bw = i
                    break

        self.writeRegister(
            REG_MODEM_CONFIG_1,
            (self.readRegister(REG_MODEM_CONFIG_1) & 0x0F) | (bw << 4),
        )

    def setCodingRate(self, denominator):
        denominator = min(max(denominator, 5), 8)
        cr = denominator - 4
        self.writeRegister(
            REG_MODEM_CONFIG_1,
            (self.readRegister(REG_MODEM_CONFIG_1) & 0xF1) | (cr << 1),
        )

    def setPreambleLength(self, length):
        self.writeRegister(REG_PREAMBLE_MSB, (length >> 8) & 0xFF)
        self.writeRegister(REG_PREAMBLE_LSB, (length >> 0) & 0xFF)

    def enableCRC(self, enable_CRC=False):
        modem_config_2 = self.readRegister(REG_MODEM_CONFIG_2)
        config = modem_config_2 | 0x04 if enable_CRC else modem_config_2 & 0xFB
        self.writeRegister(REG_MODEM_CONFIG_2, config)

    def invertIQ(self, invertIQ):
        self.parameters["invertIQ"] = invertIQ
        if invertIQ:
            self.writeRegister(
                REG_INVERTIQ,
                (
                    (
                        self.readRegister(REG_INVERTIQ)
                        & RFLR_INVERTIQ_TX_MASK
                        & RFLR_INVERTIQ_RX_MASK
                    )
                    | RFLR_INVERTIQ_RX_ON
                    | RFLR_INVERTIQ_TX_ON
                ),
            )
            self.writeRegister(REG_INVERTIQ2, RFLR_INVERTIQ2_ON)
        else:
            self.writeRegister(
                REG_INVERTIQ,
                (
                    (
                        self.readRegister(REG_INVERTIQ)
                        & RFLR_INVERTIQ_TX_MASK
                        & RFLR_INVERTIQ_RX_MASK
                    )
                    | RFLR_INVERTIQ_RX_OFF
                    | RFLR_INVERTIQ_TX_OFF
                ),
            )
            self.writeRegister(REG_INVERTIQ2, RFLR_INVERTIQ2_OFF)

    def setSyncWord(self, sw):
        self.writeRegister(REG_SYNC_WORD, sw)

    def setChannel(self, parameters):
        self.standby()
        for key in parameters:
            if key == "frequency":
                self.setFrequency(parameters[key])
                continue
            if key == "invert_IQ":
                self.invertIQ(parameters[key])
                continue
            if key == "tx_power_level":
                self.setTxPower(parameters[key])
                continue

    def dumpRegisters(self):
        # TODO end=''
        for i in range(128):
            print("0x{:02X}: {:02X}".format(i, self.readRegister(i)), end="")
            if (i + 1) % 4 == 0:
                print()
            else:
                print(" | ", end="")

    def implicitHeaderMode(self, implicitHeaderMode=False):
        if (
            self.implicit_header_mode != implicitHeaderMode
        ):  # set value only if different.
            self.implicit_header_mode = implicitHeaderMode
            modem_config_1 = self.readRegister(REG_MODEM_CONFIG_1)
            config = (
                modem_config_1 | 0x01
                if implicitHeaderMode
                else modem_config_1 & 0xFE
            )
            self.writeRegister(REG_MODEM_CONFIG_1, config)

    def receive(self, size=0):
        self.implicitHeaderMode(size > 0)
        if size > 0:
            self.writeRegister(REG_PAYLOAD_LENGTH, size & 0xFF)

        # The last packet always starts at FIFO_RX_CURRENT_ADDR
        # no need to reset FIFO_ADDR_PTR
        self.writeRegister(
            REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_RX_CONTINUOUS
        )

    def listen(self, time=1000):
        time = min(max(time, 0), 10000)
        self.receive()

        start = ticks_ms()
        while True:
            if self.receivedPacket():
                return self.readPayload()
            if ticks_ms() - start > time:
                return None

    def onReceive(self, callback):
        self.onReceive = callback

        if "dio_0" in self.pins:
            self.pin_rx_done = Pin(self.pins["dio_0"], Pin.IN)

        if self.pin_rx_done:
            if callback:
                self.writeRegister(REG_DIO_MAPPING_1, 0x00)
                self.pin_rx_done.irq(
                    trigger=Pin.IRQ_RISING, handler=self.handleOnReceive
                )
            else:
                pass
                # TODO detach irq

    def handleOnReceive(self, event_source):
        # lock until TX_Done
        self.aquirelock(True)
        irqFlags = self.getIrqFlags()
        # RX_DONE only, irqFlags should be 0x40
        if irqFlags & IRQ_RX_DONE_MASK == IRQ_RX_DONE_MASK:
            # automatically standby when RX_DONE
            if self.onReceive:
                payload = self.readPayload()
                self.onReceive(self, payload)

        elif self.readRegister(REG_OP_MODE) != (
            MODE_LONG_RANGE_MODE | MODE_RX_SINGLE
        ):
            # no packet received.
            # reset FIFO address / # enter single RX mode
            self.writeRegister(REG_FIFO_ADDR_PTR, FifoRxBaseAddr)
            self.writeRegister(
                REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_RX_SINGLE
            )

        self.aquirelock(False)  # unlock in any case.
        self.collectGarbage()
        return True

    def receivedPacket(self, size=0):
        irqFlags = self.getIrqFlags()
        self.implicitHeaderMode(size > 0)
        if size > 0:
            self.writeRegister(REG_PAYLOAD_LENGTH, size & 0xFF)

        # if (irqFlags & IRQ_RX_DONE_MASK) and \
        # (irqFlags & IRQ_RX_TIME_OUT_MASK == 0) and \
        # (irqFlags & IRQ_PAYLOAD_CRC_ERROR_MASK == 0):

        if (
            irqFlags == IRQ_RX_DONE_MASK
        ):  # RX_DONE only, irqFlags should be 0x40
            # automatically standby when RX_DONE
            return True

        elif self.readRegister(REG_OP_MODE) != (
            MODE_LONG_RANGE_MODE | MODE_RX_SINGLE
        ):
            # no packet received.
            # reset FIFO address / # enter single RX mode
            self.writeRegister(REG_FIFO_ADDR_PTR, FifoRxBaseAddr)
            self.writeRegister(
                REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_RX_SINGLE
            )

    def readPayload(self):
        # set FIFO address to current RX address
        # fifo_rx_current_addr = self.readRegister(REG_FIFO_RX_CURRENT_ADDR)
        self.writeRegister(
            REG_FIFO_ADDR_PTR, self.readRegister(REG_FIFO_RX_CURRENT_ADDR)
        )

        # read packet length
        packet_length = 0
        if self.implicit_header_mode:
            packet_length = self.readRegister(REG_PAYLOAD_LENGTH)
        else:
            packet_length = self.readRegister(REG_RX_NB_BYTES)

        payload = bytearray()
        for i in range(packet_length):
            payload.append(self.readRegister(REG_FIFO))

        self.collectGarbage()
        return bytes(payload)

    def readRegister(self, address, byteorder="big", signed=False):
        response = self.transfer(address & 0x7F)
        return int.from_bytes(response, byteorder)

    def writeRegister(self, address, value):
        self.transfer(address | 0x80, value)

    def transfer(self, address, value=0x00):
        response = bytearray(1)

        self.pin_ss.value(0)

        self.spi.write(bytes([address]))
        self.spi.write_readinto(bytes([value]), response)

        self.pin_ss.value(1)

        return response

    def collectGarbage(self):
        gc.collect()
        # print('[Mem aft - free: {}   allocated: {}]'.format(gc.mem_free(), gc.mem_alloc()))
