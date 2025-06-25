from libs.i2c.BME280 import BME280
from libs.i2c.MPU6050 import MPU6050
from libs.i2c.VEML6040 import VEML6040
from libs.i2c.VL53L0X import VL53L0X
from libs.general.RotaryEncoder import RotaryEncoder
from libs.general.NeoPixelPlus import NeoPixelPlus
from libs.general.BuzzerPlus import BuzzerPlus
from libs.general.ServoPlus import ServoPlus

_SLOT_MAP = {
    'A': (0, 0, 1),
    'B': (1, 2, 3),
    'D': (0, 4, 5),
    'C': (None, 28, 22),
    'E': (1, 6, 7),
    'F': (1, 26, 27),
    'G': (0, 16, 17),
    'H': (1, 18, 19),
}

def get_slot_pins(slot):
    slot = slot.upper()[0]
    if slot not in _SLOT_MAP:
        raise ValueError(f"Invalid slot '{slot}'. Use A, B, C, D, E, or F (C is not I2C-compatible)")
    bus, sda, scl = _SLOT_MAP[slot]
    return (bus, sda, scl)

class ClimateSensor(BME280):
    def __init__(self, slot, soft_i2c=False):
        super().__init__(*get_slot_pins(slot), soft_i2c=soft_i2c)

class GyroAxelSensor(MPU6050):
    def __init__(self, slot, soft_i2c=False):
        super().__init__(*get_slot_pins(slot), soft_i2c=soft_i2c)

class ColorSensor(VEML6040):
    def __init__(self, slot, soft_i2c=False):
        super().__init__(*get_slot_pins(slot), soft_i2c=soft_i2c)

class DistanceSensor(VL53L0X):
    def __init__(self, slot, soft_i2c=False):
        super().__init__(*get_slot_pins(slot), soft_i2c=soft_i2c)

class EncoderSensor(RotaryEncoder):
    def __init__(self, slot):
        _, sda, scl = get_slot_pins(slot)
        super().__init__(clk=sda, dt=scl)
        
class Buzzer(BuzzerPlus):
    def __init__(self, slot):
        _, sda, _ = get_slot_pins(slot)
        super().__init__(pin=sda)

class LEDTower(NeoPixelPlus):
    def __init__(self, pin, led_num=8):
        super().__init__(pin=pin, led_num=led_num)
