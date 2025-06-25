# MPU-6050 Simple MicroPython Library with Tilt Event Support
# MIT License

from machine import I2C, Pin, SoftI2C
import time

class MPU6050:
    def __init__(self, bus, sda, scl, address=0x68, soft_i2c=False):
        self.bus = bus
        self.sda = sda
        self.scl = scl
        self.address = address
        self.soft_i2c = soft_i2c

        if self.soft_i2c:
            self.i2c = SoftI2C(Pin(self.scl), Pin(self.sda))
        else:
            self.i2c = I2C(self.bus, scl=Pin(self.scl), sda=Pin(self.sda))
        
        try:
            self.wake()
            time.sleep_ms(100)
        except Exception as e:
            raise RuntimeError("Failed to wake up GyroAxel. Check wiring and connection.") from e

        self._tilt_listeners = {
            "forward": [],
            "backward": [],
            "left": [],
            "right": []
        }
        self._tilt_threshold = 0.4

    def wake(self):
        self.i2c.writeto_mem(self.address, 0x6B, b'\x00')

    def sleep(self):
        self.i2c.writeto_mem(self.address, 0x6B, b'\x40')

    def read_temperature(self):
        data = self.i2c.readfrom_mem(self.address, 0x41, 2)
        raw = self._combine(data[0], data[1])
        return (raw / 340.0) + 36.53

    def read_accel_data(self):
        data = self.i2c.readfrom_mem(self.address, 0x3B, 6)
        x = self._combine(data[0], data[1]) / 16384.0
        y = self._combine(data[2], data[3]) / 16384.0
        z = self._combine(data[4], data[5]) / 16384.0
        return (x, y, z)

    def read_gyro_data(self):
        data = self.i2c.readfrom_mem(self.address, 0x43, 6)
        x = self._combine(data[0], data[1]) / 131.0
        y = self._combine(data[2], data[3]) / 131.0
        z = self._combine(data[4], data[5]) / 131.0
        return (x, y, z)

    def add_tilt_listener(self, direction, callback):
        if direction not in self._tilt_listeners:
            raise ValueError("Direction must be 'forward', 'backward', 'left', or 'right'")
        self._tilt_listeners[direction].append(callback)

    def check_tilt(self):
        x, y, _ = self.read_accel_data()
        if x > self._tilt_threshold:
            for fn in self._tilt_listeners["forward"]:
                fn()
        elif x < -self._tilt_threshold:
            for fn in self._tilt_listeners["backward"]:
                fn()
        if y > self._tilt_threshold:
            for fn in self._tilt_listeners["left"]:
                fn()
        elif y < -self._tilt_threshold:
            for fn in self._tilt_listeners["right"]:
                fn()

    def _combine(self, high, low):
        value = (high << 8) | low
        return value - 65536 if value >= 0x8000 else value
