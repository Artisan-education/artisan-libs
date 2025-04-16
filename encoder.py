# Made for Artisan pibody robotics kit
# by: Alikhan Yessaly, Apr. 2025

from machine import Pin

# Rotary decoding constants
_DIR_CW = const(0x10)
_DIR_CCW = const(0x20)
_R_START = const(0x0)
_STATE_MASK = const(0x07)
_DIR_MASK = const(0x30)

_transition_table = [
    [_R_START, 4, 1,  _R_START],
    [2,  _R_START, 1,  _R_START],
    [2,  3,  1,  _R_START],
    [2,  3,  _R_START, _R_START | _DIR_CW],
    [5,  4,  _R_START, _R_START],
    [5,  4,  6,  _R_START],
    [5,  _R_START, 6,  _R_START | _DIR_CCW],
    [_R_START, _R_START, _R_START, _R_START]
]

_SLOT_MAP = {
    'A': (0, 1),
    'B': (2, 3),
    'C': (28, 22),
    'D': (4, 5),
    'E': (6, 7),
    'F': (26, 27),
}

class RotaryEncoder:
    def __init__(self,
                 slot,
                 min_val=0,
                 max_val=100,
                 incr=1,
                 reverse=False,
                 wrap=True,
                 pull_up=False):
        if slot not in _SLOT_MAP:
            raise ValueError(f"Invalid slot '{slot}'. Choose from A–F.")

        self._clk_pin, self._dt_pin = _SLOT_MAP[slot]
        self._min = min_val
        self._max = max_val
        self._value = min_val
        self._incr = incr
        self._wrap = wrap
        self._reverse = -1 if reverse else 1
        self._state = _R_START
        self._listeners = []

        mode = Pin.IN | (Pin.PULL_UP if pull_up else 0)
        self._clk = Pin(self._clk_pin, mode)
        self._dt = Pin(self._dt_pin, mode)

        self._clk.irq(self._process, Pin.IRQ_RISING | Pin.IRQ_FALLING)
        self._dt.irq(self._process, Pin.IRQ_RISING | Pin.IRQ_FALLING)

    def _process(self, pin):
        clk_dt = (self._clk.value() << 1) | self._dt.value()
        self._state = _transition_table[self._state & _STATE_MASK][clk_dt]
        direction = self._state & _DIR_MASK
        if direction == 0:
            return

        step = self._incr * self._reverse
        new_val = self._value + (step if direction == _DIR_CW else -step)

        if self._wrap:
            rng = self._max - self._min + 1
            new_val = self._min + (new_val - self._min) % rng
        else:
            new_val = min(self._max, max(self._min, new_val))

        if new_val != self._value:
            self._value = new_val
            for cb in self._listeners:
                cb(self._value, step if direction == _DIR_CW else -step)

    def bar(self, width=20, fill_char="#", empty_char=" "):
        pos = int((self._value - self._min) / (self._max - self._min) * width)
        filled = fill_char * pos
        empty = empty_char * (width - pos)
        return f"[{filled}{empty}] {self._value}"
    
    def live_bar(self, width=20, fill_char="#", empty_char=" "):
        pos = int((self._value - self._min) / (self._max - self._min) * width)
        filled = fill_char * pos
        empty = empty_char * (width - pos)
        print(f"\r[{filled}{empty}] {self._value}   ", end="")
    
    def value(self):
        return self._value

    def reset(self, to=0):
        self._value = to

    def add_listener(self, fn):
        self._listeners.append(fn)