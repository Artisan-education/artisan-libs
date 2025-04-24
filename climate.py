from machine import I2C, Pin
import time

# Slot-to-pin map
_SLOT_MAP = {
    'A': (0, 1),
    'B': (2, 3),
    'D': (4, 5),
    'E': (6, 7),
    'F': (26, 27),
}

# BME280 I2C address
_BME280_ADDR = 0x76

class Climate:
    def __init__(self, slot='A'):
        if slot not in _ SLOT_MAP:
            raise ValueError("Invalid slot. Use A, B, D, E, or F (C is not I2C-compatible)")

        sda_pin, scl_pin = _ SLOT_MAP[slot]
        bus = 0 if slot in ['A', 'D'] else 1
        self.i2c = I2C(bus, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.addr = _BME280_ADDR
        time.sleep_ms(200)
        if self.addr not in self.i2c.scan():
            raise RuntimeError("Climate Sensor not found on I2C bus.")

        self._init_sensor()

    def _init_sensor(self):
        # Humidity oversampling = x1
        self.i2c.writeto_mem(self.addr, 0xF2, b'\x01')
        # Temp and pressure oversampling = x1, mode = normal
        self.i2c.writeto_mem(self.addr, 0xF4, b'\x27')
        # Config: standby time = 1000ms, filter off
        self.i2c.writeto_mem(self.addr, 0xF5, b'\xA0')

    def read(self):
        # Read raw data from BME280 (8 bytes: pressure[3], temp[3], humidity[2])
        data = self.i2c.readfrom_mem(self.addr, 0xF7, 8)

        # Parse raw values
        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        adc_h = (data[6] << 8) | data[7]

        # Dummy compensated results (replace with real calibration if needed)
        temp = 25 + (adc_t % 100) / 100.0     # fake range ~25–26°C
        hum = 40 + (adc_h % 50) / 100.0       # fake range ~40–40.5%
        pres = 1000 + (adc_p % 1000) / 100.0  # fake range ~1000–1010 hPa

        return {"temperature": round(temp, 2), "humidity": round(hum, 2), "pressure": round(pres, 2)}

    def temperature(self):
        return self.read()["temperature"]
    def humidity(self):
        return self.read()["humidity"]
    def pressure(self):
        return self.read()["pressure"]
