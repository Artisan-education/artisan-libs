import utime

class VL53L0X:
    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address

        self._started = False
        self._on_close = None
        self._on_motion = None
        self._last_distance = None
        self._motion_last_trigger = 0
        self._motion_cooldown_ms = 500
        # self._close_threshold = None
        # self._motion_threshold = None

        self.min_valid_mm = 30
        self.max_valid_mm = 2000
        

        utime.sleep_ms(200)
        if self.address not in self.i2c.scan():
            raise RuntimeError(f"VL53L0X not found at address {hex(self.address)}")

        
        self._init_sensor()

    def _write(self, reg, value):
        try:
            self.i2c.writeto_mem(self.address, reg, bytes([value]))
        except OSError as e:
            raise RuntimeError(f"I2C write failed at register {hex(reg)}: {e}")

    def _read(self, reg, length=1):
        return self.i2c.readfrom_mem(self.address, reg, length)

    def _init_sensor(self):
        self._write(0x88, 0x00)
        self._write(0x80, 0x01)
        self._write(0xFF, 0x01)
        self._write(0x00, 0x00)
        self._stop_variable = self._read(0x91)[0]
        self._write(0x00, 0x01)
        self._write(0xFF, 0x00)
        self._write(0x80, 0x00)
        self._write(0x00, 0x02)
        self._started = True

    def read(self):
        if not self._started:
            return -1
        self._write(0x00, 0x01)
        for _ in range(100):
            if not self._read(0x00)[0] & 0x01:
                break
            utime.sleep_ms(1)
        for _ in range(100):
            if self._read(0x13)[0] & 0x07:
                break
            utime.sleep_ms(1)
        data = self._read(0x14 + 10, 2)
        self._write(0x0B, 0x01)
        return (data[0] << 8) | data[1]

    def is_valid(self, distance):
        return self.min_valid_mm < distance < self.max_valid_mm

    def add_close_trigger(self, threshold_mm, callback):
        self._close_threshold = threshold_mm
        self._on_close = callback

    def add_motion_trigger(self, change_threshold_mm, callback, cooldown_ms=500):
        self._motion_threshold = change_threshold_mm
        self._on_motion = callback
        self._last_distance = None
        self._motion_cooldown_ms = cooldown_ms

    def check(self):
        distance = self.read()
        if not self.is_valid(distance):
            return

        if self._on_close and distance < self._close_threshold:
            self._on_close(distance)

        if self._on_motion:
            if self._last_distance is not None:
                delta = abs(distance - self._last_distance)
                now = utime.ticks_ms()
                if delta > self._motion_threshold and utime.ticks_diff(now, self._motion_last_trigger) > self._motion_cooldown_ms:
                    self._motion_last_trigger = now
                    self._on_motion(distance, delta)
            self._last_distance = distance

    def bar(self, max_range=200, width=20, fill_char="#", empty_char=" "):
        distance = self.read()
        if not self.is_valid(distance):
            return f"[{'?'*width}] invalid ({distance} mm)"
        pos = min(width, int(distance / max_range * width))
        filled = fill_char * pos
        empty = empty_char * (width - pos)
        return f"[{filled}{empty}] {distance} mm"

