from machine import Pin
from time import sleep_ms

_DIR_CW = 0x10
_DIR_CCW = 0x20

_R_START = 0x0
_R_CW_1 = 0x1
_R_CW_2 = 0x2
_R_CW_3 = 0x3
_R_CCW_1 = 0x4
_R_CCW_2 = 0x5
_R_CCW_3 = 0x6
_R_ILLEGAL = 0x7

_transition_table = [
    [_R_START, _R_CCW_1, _R_CW_1,  _R_START],
    [_R_CW_2,  _R_START, _R_CW_1,  _R_START],
    [_R_CW_2,  _R_CW_3,  _R_CW_1,  _R_START],
    [_R_CW_2,  _R_CW_3,  _R_START, _R_START | _DIR_CW],
    [_R_CCW_2, _R_CCW_1, _R_START, _R_START],
    [_R_CCW_2, _R_CCW_1, _R_CCW_3, _R_START],
    [_R_CCW_2, _R_START, _R_CCW_3, _R_START | _DIR_CCW],
    [_R_START, _R_START, _R_START, _R_START]]

_transition_table_half_step = [
    [_R_CW_3,            _R_CW_2,  _R_CW_1,  _R_START],
    [_R_CW_3 | _DIR_CCW, _R_START, _R_CW_1,  _R_START],
    [_R_CW_3 | _DIR_CW,  _R_CW_2,  _R_START, _R_START],
    [_R_CW_3,            _R_CCW_2, _R_CCW_1, _R_START],
    [_R_CW_3,            _R_CW_2,  _R_CCW_1, _R_START | _DIR_CW],
    [_R_CW_3,            _R_CCW_2, _R_CW_3,  _R_START | _DIR_CCW],
    [_R_START,           _R_START, _R_START, _R_START],
    [_R_START,           _R_START, _R_START, _R_START]]

_STATE_MASK = 0x07
_DIR_MASK = 0x30

_SLOT_MAP = {
    'A': (0, 1), 'B': (2, 3), 'C': (28, 22), 'D': (4, 5),
    'E': (6, 7), 'F': (26, 27)
}

def _wrap(value, incr, lower_bound, upper_bound):
    range_ = upper_bound - lower_bound + 1
    value = value + incr
    if value < lower_bound:
        value += range_ * ((lower_bound - value) // range_ + 1)
    return lower_bound + (value - lower_bound) % range_

def _bound(value, incr, lower_bound, upper_bound):
    return min(upper_bound, max(lower_bound, value + incr))

def _trigger(rotary_instance):
    for listener in rotary_instance._listener:
        listener()

def _irq_supported():
    try:
        p = Pin(20, Pin.IN)
        p.irq(lambda pin: None, Pin.IRQ_FALLING)
        return True
    except:
        return False

class Encoder:
    RANGE_UNBOUNDED = 1
    RANGE_WRAP = 2
    RANGE_BOUNDED = 3

    def __init__(self, slot, min_val=0, max_val=10, incr=1,
                 reverse=False, range_mode=RANGE_UNBOUNDED,
                 half_step=False, invert=False, pull_up=False):

        if slot not in _SLOT_MAP:
            raise ValueError(f"Invalid slot '{slot}'. Choose from A–F.")

        self._clk_pin, self._dt_pin = _SLOT_MAP[slot]
        self._min_val = min_val
        self._max_val = max_val
        self._incr = incr
        self._reverse = -1 if reverse else 1
        self._range_mode = range_mode
        self._value = min_val
        self._state = _R_START
        self._half_step = half_step
        self._invert = invert
        self._listener = []
        self._direction = 0
        self._simulate_mode = not _irq_supported()

        if pull_up:
            self._pin_clk = Pin(self._clk_pin, Pin.IN, Pin.PULL_UP)
            self._pin_dt = Pin(self._dt_pin, Pin.IN, Pin.PULL_UP)
        else:
            self._pin_clk = Pin(self._clk_pin, Pin.IN)
            self._pin_dt = Pin(self._dt_pin, Pin.IN)

        if not self._simulate_mode:
            self._hal_enable_irq()

    def _hal_enable_irq(self):
        self._pin_clk.irq(self._process_rotary_pins, Pin.IRQ_RISING | Pin.IRQ_FALLING)
        self._pin_dt.irq(self._process_rotary_pins, Pin.IRQ_RISING | Pin.IRQ_FALLING)

    def _hal_disable_irq(self):
        self._pin_clk.irq(None)
        self._pin_dt.irq(None)

    def _read_encoder(self):
        clk_dt_pins = (self._pin_clk.value() << 1) | self._pin_dt.value()
        if self._invert:
            clk_dt_pins = ~clk_dt_pins & 0x03

        if self._half_step:
            self._state = _transition_table_half_step[self._state & _STATE_MASK][clk_dt_pins]
        else:
            self._state = _transition_table[self._state & _STATE_MASK][clk_dt_pins]

        direction = self._state & _DIR_MASK
        incr = 0
        if direction == _DIR_CW:
            incr = self._incr
            self._direction = 1
        elif direction == _DIR_CCW:
            incr = -self._incr
            self._direction = -1

        incr *= self._reverse

        if self._range_mode == self.RANGE_WRAP:
            self._value = _wrap(self._value, incr, self._min_val, self._max_val)
        elif self._range_mode == self.RANGE_BOUNDED:
            self._value = _bound(self._value, incr, self._min_val, self._max_val)
        else:
            self._value += incr

        return direction != 0

    def _process_rotary_pins(self, pin):
        old_value = self._value
        updated = self._read_encoder()
        if updated and self._listener:
            try:
                _trigger(self)
            except Exception as e:
                print("Listener error:", e)

    def value(self):
        if self._simulate_mode:
            sleep_ms(2)
            self._process_rotary_pins(None)
        return self._value

    def direction(self):
        return self._direction

    def reset(self):
        self._value = 0

    def close(self):
        if not self._simulate_mode:
            self._hal_disable_irq()

    def set(self, value=None, min_val=None, incr=None,
            max_val=None, reverse=None, range_mode=None):
        if not self._simulate_mode:
            self._hal_disable_irq()

        if value is not None:
            self._value = value
        if min_val is not None:
            self._min_val = min_val
        if max_val is not None:
            self._max_val = max_val
        if incr is not None:
            self._incr = incr
        if reverse is not None:
            self._reverse = -1 if reverse else 1
        if range_mode is not None:
            self._range_mode = range_mode

        self._state = _R_START

        if not self._simulate_mode:
            self._hal_enable_irq()

    def add_listener(self, l):
        self._listener.append(l)

    def remove_listener(self, l):
        if l in self._listener:
            self._listener.remove(l)
