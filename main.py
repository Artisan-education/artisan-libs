from machine import Pin, PWM
import time
import display
from encoder import Encoder
import random

freqs = [500, 1000, 1500]

# --- Display Setup ---
tft = display.Display()
WHITE = display.WHITE
YELLOW = display.YELLOW
BLACK = display.BLACK

# --- LED Setup ---
leds = [Pin(4, Pin.OUT), Pin(6, Pin.OUT), Pin(26, Pin.OUT)]

# --- Buzzer Setup (GP0) ---
buzzer = PWM(Pin(0))
buzzer.duty_u16(0)  # Silence initially

def beep(freq=1000, duration=80):
    buzzer.freq(freq)
    buzzer.duty_u16(900)  # Half the previous volume
    time.sleep_ms(duration)
    buzzer.duty_u16(0)

# --- Encoder Setup (Slot C = GP28, GP22) ---
enc = Encoder('C', min_val=0, max_val=6, incr=1, range_mode=2)
# --- Menu Items ---
modes = [
    " 1.Blink All",
    " 2.Chase T->B",
    " 3.Chase B->T",
    " 4.Ping-Pong",
    " 5.Rand Blink",
    " 6.Star Wars",
    " 7.Mario Song"
]

# --- UI State ---
prev_index = -1
last_index = enc.value()

def draw_menu(current_index, running=False):
    global prev_index
    if prev_index == -1:
        tft.fill(BLACK)
        tft.text("Select Mode:", 10, 10, font=3, fg=WHITE)
        for i, label in enumerate(modes):
            y = 70 + i * 30
            tft.text(label, 20, y, font=2, fg=WHITE)

    if prev_index != current_index:
        y_old = 70 + prev_index * 30
        tft.text(" ", 10, y_old, font=2, fg=WHITE)

    y = 70 + current_index * 30
    prefix = ">"
    tft.text(prefix, 10, y, font=2, fg=YELLOW)
    prev_index = current_index

# --- Patterns (1 step per call) ---
def blink_all():
    for led, f in zip(leds, freqs):
        led.on()
        beep(f, 60)
    time.sleep(0.2)
    for led in leds:
        led.off()
    time.sleep(0.2)
    
def chase_lr():
    for led, f in zip(leds, freqs):
        led.on()
        beep(f, 50)
        time.sleep(0.1)
        led.off()

def chase_rl():
    for led, f in zip(reversed(leds), reversed(freqs)):
        led.on()
        beep(f, 50)
        time.sleep(0.1)
        led.off()


def ping_pong():
    for led, f in zip(leds, freqs):
        led.on()
        beep(f, 50)
        time.sleep(0.1)
        led.off()
    for led, f in zip(reversed(leds[1:-1]), reversed(freqs[1:-1])):
        led.on()
        beep(f, 50)
        time.sleep(0.1)
        led.off()


def random_blink():
    i = random.randint(0, 2)
    leds[i].on()
    beep(freqs[i], 80)
    time.sleep(0.2)
    leds[i].off()
    time.sleep(0.1)

def star_wars_theme():
    active_index = last_index

    # Imperial March – Shortened
    melody = [
        (440, 500), (440, 500), (440, 500),
        (349, 350), (523, 150),
        (440, 500), (349, 350), (523, 150),
        (440, 1000),
        (659, 500), (659, 500), (659, 500),
        (698, 350), (523, 150),
        (415, 500), (349, 350), (523, 150),
        (440, 1000)
    ]

    for freq, dur in melody:
        if enc.value() != active_index:
            return

        # LED by frequency
        if freq < 500:
            led_index = 0
        elif freq < 600:
            led_index = 1
        else:
            led_index = 2

        for i, led in enumerate(leds):
            led.value(i == led_index)

        beep(freq, dur)
        time.sleep_ms(50)

    for led in leds:
        led.off()



def mario_theme():
    active_index = last_index  # lock in current mode

    melody = [
        (660, 100), (660, 100), (0, 100), (660, 100),
        (0, 100), (523, 100), (660, 100), (0, 100), (784, 100),
        (0, 300), (392, 100), (0, 300),

        (523, 100), (0, 100), (392, 100), (0, 100),
        (330, 100), (0, 100), (440, 100), (0, 100), (494, 100),
        (0, 100), (466, 100), (440, 100), (0, 200),

        (392, 100), (660, 100), (784, 100), (880, 100),
        (698, 100), (784, 100), (660, 100), (523, 100),
        (587, 100), (494, 100)
    ]

    for freq, dur in melody:
        if enc.value() != active_index:
            return

        # LED mapping
        if freq == 0:
            for led in leds:
                led.off()
            time.sleep_ms(dur)
            continue


        if freq < 700:
            led_index = 0
        elif freq < 1000:
            led_index = 1
        else:
            led_index = 2

        for i, led in enumerate(leds):
            led.value(i == led_index)

        beep(freq, dur)
        time.sleep_ms(30)

    for led in leds:
        led.off()


mode_funcs = [
    blink_all,
    chase_lr,
    chase_rl,
    ping_pong,
    random_blink,
    star_wars_theme,
    mario_theme  # <-- new one
]
# --- Run Mode with Live Encoder Check ---
def run_mode(func):
    global last_index
    active_index = last_index
    draw_menu(last_index, running=True)
    beep(1500, 120)  # Start beep
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 5000:
        current_index = enc.value()
        if current_index != last_index:
            draw_menu(current_index)
            last_index = current_index
            return
        func()
    draw_menu(last_index, running=False)

# --- Main Loop ---
draw_menu(last_index)

while True:
    current_index = enc.value()
    if current_index != last_index:
        draw_menu(current_index)
        last_index = current_index

    print(last_index, "mode completed")
    run_mode(mode_funcs[last_index])

