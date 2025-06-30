import time
# BME280 default address.
BME280_I2CADDR = 0x76

# Operating Modes
BME280_OSAMPLE_1 = 1
BME280_OSAMPLE_2 = 2
BME280_OSAMPLE_4 = 3
BME280_OSAMPLE_8 = 4
BME280_OSAMPLE_16 = 5

# BME280 Registers

BME280_REGISTER_DIG_T1 = 0x88  # Trimming parameter registers
BME280_REGISTER_DIG_T2 = 0x8A
BME280_REGISTER_DIG_T3 = 0x8C

BME280_REGISTER_DIG_P1 = 0x8E
BME280_REGISTER_DIG_P2 = 0x90
BME280_REGISTER_DIG_P3 = 0x92
BME280_REGISTER_DIG_P4 = 0x94
BME280_REGISTER_DIG_P5 = 0x96
BME280_REGISTER_DIG_P6 = 0x98
BME280_REGISTER_DIG_P7 = 0x9A
BME280_REGISTER_DIG_P8 = 0x9C
BME280_REGISTER_DIG_P9 = 0x9E

BME280_REGISTER_DIG_H1 = 0xA1
BME280_REGISTER_DIG_H2 = 0xE1
BME280_REGISTER_DIG_H3 = 0xE3
BME280_REGISTER_DIG_H4 = 0xE4
BME280_REGISTER_DIG_H5 = 0xE5
BME280_REGISTER_DIG_H6 = 0xE6
BME280_REGISTER_DIG_H7 = 0xE7

BME280_REGISTER_CHIPID = 0xD0
BME280_REGISTER_VERSION = 0xD1
BME280_REGISTER_SOFTRESET = 0xE0

BME280_REGISTER_CONTROL_HUM = 0xF2
BME280_REGISTER_CONTROL = 0xF4
BME280_REGISTER_CONFIG = 0xF5
BME280_REGISTER_PRESSURE_DATA = 0xF7
BME280_REGISTER_TEMP_DATA = 0xFA
BME280_REGISTER_HUMIDITY_DATA = 0xFD

_BME280_ADDR = 0x76

class BME280:
    def __init__(self, i2c, mode=BME280_OSAMPLE_1):
        if mode not in [BME280_OSAMPLE_1, BME280_OSAMPLE_2, BME280_OSAMPLE_4, BME280_OSAMPLE_8, BME280_OSAMPLE_16]:
            raise ValueError(
                'Unexpected mode value {0}. Set mode to one of '
                'BME280_ULTRALOWPOWER, BME280_STANDARD, BME280_HIGHRES, or '
                'BME280_ULTRAHIGHRES'.format(mode))
        self._mode = mode
        self._i2c = i2c
        self._address = _BME280_ADDR
        time.sleep_ms(100)
        if self._address not in self._i2c.scan():
            raise RuntimeError("Climate Sensor not found on I2C bus.")

        self._init_sensor()

    def _init_sensor(self):
        # Humidity oversampling = x1
        self._load_calibration()
        self._write8(BME280_REGISTER_CONTROL, 0x3F)
        self.t_fine = 0

    def _load_calibration(self):
        self.dig_T1 = self._readU16LE(BME280_REGISTER_DIG_T1)
        self.dig_T2 = self._readS16LE(BME280_REGISTER_DIG_T2)
        self.dig_T3 = self._readS16LE(BME280_REGISTER_DIG_T3)

        self.dig_P1 = self._readU16LE(BME280_REGISTER_DIG_P1)
        self.dig_P2 = self._readS16LE(BME280_REGISTER_DIG_P2)
        self.dig_P3 = self._readS16LE(BME280_REGISTER_DIG_P3)
        self.dig_P4 = self._readS16LE(BME280_REGISTER_DIG_P4)
        self.dig_P5 = self._readS16LE(BME280_REGISTER_DIG_P5)
        self.dig_P6 = self._readS16LE(BME280_REGISTER_DIG_P6)
        self.dig_P7 = self._readS16LE(BME280_REGISTER_DIG_P7)
        self.dig_P8 = self._readS16LE(BME280_REGISTER_DIG_P8)
        self.dig_P9 = self._readS16LE(BME280_REGISTER_DIG_P9)

        self.dig_H1 = self._readU8(BME280_REGISTER_DIG_H1)
        self.dig_H2 = self._readS16LE(BME280_REGISTER_DIG_H2)
        self.dig_H3 = self._readU8(BME280_REGISTER_DIG_H3)
        self.dig_H6 = self._readS8(BME280_REGISTER_DIG_H7)

        h4 = self._readS8(BME280_REGISTER_DIG_H4)
        h4 = (h4 << 24) >> 20
        self.dig_H4 = h4 | (self._readU8(BME280_REGISTER_DIG_H5) & 0x0F)

        h5 = self._readS8(BME280_REGISTER_DIG_H6)
        h5 = (h5 << 24) >> 20
        self.dig_H5 = h5 | (
            self._readU8(BME280_REGISTER_DIG_H5) >> 4 & 0x0F)

    def _readU16LE(self, register):
        result = int.from_bytes(
            self._i2c.readfrom_mem(self._address, register, 2),'little') & 0xFFFF
        return result

    def _readS16LE(self, register):
        result = self._readU16LE(register)
        if result > 32767:
          result -= 65536
        return result

    def _readU8(self, register):
        return int.from_bytes(
            self._i2c.readfrom_mem(self._address, register, 1),'little') & 0xFF

    def _write8(self, register, value):
        b=bytearray(1)
        b[0]=value & 0xFF
        self._i2c.writeto_mem(self._address, register, b)

    def _readS8(self, register):
        result = self._readU8(register)
        if result > 127:
          result -= 256
        return result

    def read_raw_temp(self):
        """Reads the raw (uncompensated) temperature from the sensor."""
        meas = self._mode
        self._write8(BME280_REGISTER_CONTROL_HUM, meas)
        meas = self._mode << 5 | self._mode << 2 | 1
        self._write8(BME280_REGISTER_CONTROL, meas)
        sleep_time = 1250 + 2300 * (1 << self._mode)

        sleep_time = sleep_time + 2300 * (1 << self._mode) + 575
        sleep_time = sleep_time + 2300 * (1 << self._mode) + 575
        time.sleep_us(sleep_time)  # Wait the required time
        msb = self._readU8(BME280_REGISTER_TEMP_DATA)
        lsb = self._readU8(BME280_REGISTER_TEMP_DATA + 1)
        xlsb = self._readU8(BME280_REGISTER_TEMP_DATA + 2)
        raw = ((msb << 16) | (lsb << 8) | xlsb) >> 4
        return raw

    def read_raw_pressure(self):
        """Reads the raw (uncompensated) pressure level from the sensor."""
        """Assumes that the temperature has already been read """
        """i.e. that enough delay has been provided"""
        msb = self._readU8(BME280_REGISTER_PRESSURE_DATA)
        lsb = self._readU8(BME280_REGISTER_PRESSURE_DATA + 1)
        xlsb = self._readU8(BME280_REGISTER_PRESSURE_DATA + 2)
        raw = ((msb << 16) | (lsb << 8) | xlsb) >> 4
        return raw

    def read_raw_humidity(self):
        """Assumes that the temperature has already been read """
        """i.e. that enough delay has been provided"""
        msb = self._readU8(BME280_REGISTER_HUMIDITY_DATA)
        lsb = self._readU8(BME280_REGISTER_HUMIDITY_DATA + 1)
        raw = (msb << 8) | lsb
        return raw

    def read_temperature(self):
        """Get the compensated temperature in 0.01 of a degree celsius."""
        adc = self.read_raw_temp()
        var1 = ((adc >> 3) - (self.dig_T1 << 1)) * (self.dig_T2 >> 11)
        var2 = ((
            (((adc >> 4) - self.dig_T1) * ((adc >> 4) - self.dig_T1)) >> 12) *
            self.dig_T3) >> 14
        self.t_fine = var1 + var2
        T = (self.t_fine * 5 + 128) >> 8
        return  T / 100

    def read_pressure(self):
        """Gets the compensated pressure in Pascals."""
        adc = self.read_raw_pressure()
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = (((var1 * var1 * self.dig_P3) >> 8) +
                ((var1 * self.dig_P2) >> 12))
        var1 = (((1 << 47) + var1) * self.dig_P1) >> 33
        if var1 == 0:
          return 0
        p = 1048576 - adc
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.dig_P8 * p) >> 19
        P = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)
        return P / 256 / 100

    def read_humidity(self):
        adc = self.read_raw_humidity()
        # print 'Raw humidity = {0:d}'.format (adc)
        h = self.t_fine - 76800
        h = (((((adc << 14) - (self.dig_H4 << 20) - (self.dig_H5 * h)) +
             16384) >> 15) * (((((((h * self.dig_H6) >> 10) * (((h *
                              self.dig_H3) >> 11) + 32768)) >> 10) + 2097152) *
                              self.dig_H2 + 8192) >> 14))
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * self.dig_H1) >> 4)
        h = 0 if h < 0 else h
        h = 419430400 if h > 419430400 else h
        H = h >> 12
        return H / 1024

    def read(self):
        temp = self.read_temperature()
        humi = self.read_humidity()
        pres = self.read_pressure()

        return {"temperature": round(temp, 2), "humidity": round(humi, 2), "pressure": round(pres, 2)}
