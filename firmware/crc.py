# crc.py, firmware v7
# CRC8 DVB-S2: polynomial 0xD5, init 0, no reflection, no final XOR.
# Used by the RunCam Device Protocol and by CRSF.


def crc8_dvb_s2_byte(crc, b):
    crc ^= b
    for _ in range(8):
        if crc & 0x80:
            crc = ((crc << 1) ^ 0xD5) & 0xFF
        else:
            crc = (crc << 1) & 0xFF
    return crc


def crc8_dvb_s2(data, crc=0):
    for b in data:
        crc = crc8_dvb_s2_byte(crc, b)
    return crc


def hexs(data):
    return " ".join("%02X" % b for b in data)
