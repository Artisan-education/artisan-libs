from machine import Pin, PWM
import time
class BuzzerPlus:
    def __init__(self, pin):
        self.buzzer = PWM(Pin(pin))
        self.buzzer.duty_u16(0)
        self._volume = 1.0
        self._duty_cycle = 32768
        self._freq = 1000

    def freq(self, frequency=None):
        if frequency is None:
            return self._freq
        else:
            self._freq = frequency
            self.buzzer.freq(frequency)

    def duty_u16(self, duty_cycle=None):
        if duty_cycle is None:
            return self.duty_cycle()
        else:
            self._duty_cycle = duty_cycle
            self.buzzer.duty_u16(duty_cycle)


    def duty_cycle(self):
        self._duty_cycle = int(32768 * self._volume)
        return self._duty_cycle

    def volume(self, volume=None):
        if volume is None:
            return self._volume
        else:
            self._volume = volume
            self.duty_cycle()


    def beep(self, freq=None, volume=None, duration=0.1):
        if freq is None:
            freq = self._freq
        if volume is None:
            volume = self._volume
        self.freq(freq)
        self.volume(volume)

        self.buzzer.duty_u16(self.duty_cycle())
        time.sleep(duration)
        self.buzzer.duty_u16(0)
        
    def on(self, freq=None, volume=None):
        if freq is None:
            freq = self._freq
        self.buzzer.duty_u16(self.duty_cycle())

    def off(self):
        self.buzzer.duty_u16(0)
