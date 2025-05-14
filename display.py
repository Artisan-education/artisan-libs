"""
display.py - MicroPython ST7789 driver for Raspberry Pi Pico Pibody.
"""

import time
import struct
from machine import SPI, Pin

# VGA font modules
import fonts.large   as font3
import fonts.medium  as font2
import fonts.small   as font1

# Color constants (RGB565)
BLACK   = 0x0000
BLUE    = 0x001F
RED     = 0xF800
GREEN   = 0x07E0
CYAN    = 0x07FF
MAGENTA = 0xF81F
YELLOW  = 0xFFE0
WHITE   = 0xFFFF
BROWN   = 0x7BEF

# ST7789 command constants
_SWRESET = 0x01
_SLPOUT  = 0x11
_NORON   = 0x13
_INVOFF  = 0x20
_INVON   = 0x21
_DISPOFF = 0x28
_DISPON  = 0x29
_CASET   = 0x2A
_RASET   = 0x2B
_RAMWR   = 0x2C
_COLMOD  = 0x3A
_MADCTL  = 0x36
_VSCRDEF = 0x33
_VSCSAD  = 0x37

# MADCTL flags
_MADCTL_MY  = 0x80
_MADCTL_MX  = 0x40
_MADCTL_MV  = 0x20
_MADCTL_BGR = 0x08
_MADCTL_RGB = 0x00

# Wrap options
_OPTIONS_WRAP   = 0x01
_OPTIONS_WRAP_H = 0x02
_OPTIONS_WRAP_V = 0x04

# Color mode data
_COLOR_MODE_16BIT = 0x55  # RGB565

# Rotation tables: (madctl, width, height, xstart, ystart)
_ROT_240x320 = [
    (0x00, 240, 320, 0, 0),
    (0x60, 320, 240, 0, 0),
    (0xC0, 240, 320, 0, 0),
    (0xA0, 320, 240, 0, 0),
]
_ROT_240x240 = [
    (0x00, 240, 240, 0, 0),
    (0x60, 240, 240, 0, 0),
    (0xC0, 240, 240, 0, 80),
    (0xA0, 240, 240, 80, 0),
]

class Display:
    def __init__(
        self,
        spi_bus=1,
        sck=10,
        mosi=11,
        dc_pin=14,
        rst_pin=13,
        cs_pin=15,
        bl_pin=None,
        width=240,
        height=320,
        rotation=2,
        color_order=_MADCTL_RGB,
        inversion=True,
        options=0,
    ):
        """
        Initialize ST7789 driver.

        spi_bus: SPI bus number
        sck, mosi: pins for SPI
        dc_pin, rst_pin, cs_pin, bl_pin: control lines
        width, height: panel dimensions
        rotation: 0-3
        color_order: _MADCTL_RGB or _MADCTL_BGR
        inversion: True to invert display
        options: wrap flags (_OPTIONS_WRAP_H/V)
        """
        # SPI and control pins
        self.spi = SPI(
            spi_bus,
            baudrate=62500000,
            polarity=0,
            phase=0,
            sck=Pin(sck),
            mosi=Pin(mosi),
        )
        self.dc  = Pin(dc_pin, Pin.OUT)
        self.rst = Pin(rst_pin, Pin.OUT)
        self.cs  = Pin(cs_pin, Pin.OUT)
        self.bl  = Pin(bl_pin, Pin.OUT) if bl_pin is not None else None

        # store config
        self.color_order = color_order
        self.inversion = inversion
        self.options = options

        # rotation table
        self._rot_tbl = (
            _ROT_240x320 if (width, height) == (240, 320) else _ROT_240x240
        )
        

        # hardware reset and init sequence
        self.cs.value(1)
        self.rst.value(1); time.sleep_ms(50)
        self.rst.value(0); time.sleep_ms(50)
        self.rst.value(1); time.sleep_ms(150)

        self._cmd(_SLPOUT);  time.sleep_ms(120)
        self._cmd(_COLMOD); self._data(_COLOR_MODE_16BIT); time.sleep_ms(10)
        self._cmd(_INVON if self.inversion else _INVOFF)
        self._cmd(_NORON);  time.sleep_ms(10)
        self._cmd(_DISPON); time.sleep_ms(150)
        if self.bl:
            self.bl.value(1)
        # apply initial rotation
        self.set_rotation(rotation)
        # clear screen
        self.fill(0)

    @staticmethod
    def color565(r, g, b):
        """Convert 8-bit RGB to 16-bit RGB565."""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def set_rotation(self, rotation):
        """Set panel rotation: 0-3 using single transaction."""
        self._rotation = rotation % len(self._rot_tbl)
        mad, w, h, xs, ys = self._rot_tbl[self._rotation]
        self.width, self.height = w, h
        self.xstart, self.ystart = xs, ys
        val = mad | self.color_order
        # send MADCTL command and data in same CS transaction
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes([_MADCTL]))
        self.dc.value(1)
        self.spi.write(bytes([val]))
        self.cs.value(1)
    
    def rotation(self, value):
        """Alias for dynamic rotation change."""
        self.set_rotation(value)
    
    def sleep_mode(self, enable):
        """Enable or disable sleep mode."""
        self._cmd(_SLPOUT if not enable else _SLPOUT)

    def inversion_mode(self, enable):
        """Enable or disable display inversion."""
        self.inversion = enable
        self._cmd(_INVON if enable else _INVOFF)

    def _cmd(self, cmd):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def _data(self, data):
        self.cs.value(0)
        self.dc.value(1)
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(data)
        self.cs.value(1)

    def _set_window(self, x0, y0, x1, y1):
        self._cmd(_CASET)
        self._data(struct.pack('>HH', x0 + self.xstart, x1 + self.xstart))
        self._cmd(_RASET)
        self._data(struct.pack('>HH', y0 + self.ystart, y1 + self.ystart))
        self._cmd(_RAMWR)

    def fill(self, color):
        """Fill entire display with a solid color."""
        self.fill_rect(0, 0, self.width, self.height, color)

    def fill_rect(self, x, y, w, h, color):
        """Draw filled rectangle at (x,y)."""
        self._set_window(x, y, x + w - 1, y + h - 1)
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        total = w * h * 2
        buf = bytearray(256)
        for i in range(0, 256, 2):
            buf[i], buf[i+1] = hi, lo
        sent = 0
        while sent < total:
            n = min(256, total - sent)
            self._data(buf[:n])
            sent += n

    def pixel(self, x, y, color):
        """Draw single pixel, with optional wrap."""
        if self.options & _OPTIONS_WRAP_H:
            x %= self.width
        if self.options & _OPTIONS_WRAP_V:
            y %= self.height
        if 0 <= x < self.width and 0 <= y < self.height:
            self._set_window(x, y, x, y)
            hi = (color >> 8) & 0xFF
            lo = color & 0xFF
            self._data(bytes([hi, lo]))

    def hline(self, x, y, length, color):
        """Draw horizontal line."""
        if not (self.options & _OPTIONS_WRAP):
            self.fill_rect(x, y, length, 1, color)
        else:
            for i in range(length):
                self.pixel(x + i, y, color)

    def vline(self, x, y, length, color):
        """Draw vertical line."""
        if not (self.options & _OPTIONS_WRAP):
            self.fill_rect(x, y, 1, length, color)
        else:
            for i in range(length):
                self.pixel(x, y + i, color)

    def line(self, x0, y0, x1, y1, color):
        """Draw line with Bresenham optimized via h/v segments."""
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        dx = x1 - x0
        dy = abs(y1 - y0)
        err = dx // 2
        ystep = 1 if y0 < y1 else -1
        start = x0
        length = 0
        for x in range(x0, x1 + 1):
            length += 1
            err -= dy
            if err < 0:
                if length == 1:
                    px = y0 if steep else start
                    py = start if steep else y0
                    self.pixel(px, py, color)
                else:
                    if steep:
                        self.vline(y0, start, length, color)
                    else:
                        self.hline(start, y0, length, color)
                length = 0
                y0 += ystep
                start = x + 1
                err += dx
        if length > 0:
            if length == 1:
                px = y0 if steep else start
                py = start if steep else y0
                self.pixel(px, py, color)
            else:
                if steep:
                    self.vline(y0, start, length, color)
                else:
                    self.hline(start, y0, length, color)

    def rect(self, x, y, w, h, color):
        """Draw rectangle outline."""
        self.hline(x, y, w, color)
        self.hline(x, y + h - 1, w, color)
        self.vline(x, y, h, color)
        self.vline(x + w - 1, y, h, color)

    def circle(self, xm, ym, r, color):
        """Draw circle outline."""
        f = 1 - r
        dx = 1
        dy = -2 * r
        x = 0
        y = r
        for px, py in [(xm, ym + r), (xm, ym - r), (xm + r, ym), (xm - r, ym)]:
            self.pixel(px, py, color)
        while x < y:
            if f >= 0:
                y -= 1
                dy += 2
                f += dy
            x += 1
            dx += 2
            f += dx
            for px, py in [
                (xm + x, ym + y), (xm - x, ym + y),
                (xm + x, ym - y), (xm - x, ym - y),
                (xm + y, ym + x), (xm - y, ym + x),
                (xm + y, ym - x), (xm - y, ym - x)
            ]:
                self.pixel(px, py, color)

    def fill_circle(self, xm, ym, r, color):
        """Draw filled circle."""
        self.vline(xm, ym - r, 2 * r + 1, color)
        f = 1 - r
        dx = 1
        dy = -2 * r
        x = 0
        y = r
        while x < y:
            if f >= 0:
                y -= 1
                dy += 2
                f += dy
            x += 1
            dx += 2
            f += dx
            for px, py, length in [
                (xm + x, ym - y, 2 * y + 1),
                (xm + y, ym - x, 2 * x + 1),
                (xm - x, ym - y, 2 * y + 1),
                (xm - y, ym - x, 2 * x + 1)
            ]:
                self.vline(px, py, length, color)

    def blit_buffer(self, buf, x, y, w, h):
        """Blit raw RGB565 buffer to display."""
        self._set_window(x, y, x + w - 1, y + h - 1)
        self._data(buf)

    def set_window(self, x0, y0, x1, y1):
        """Alias for window setting."""
        self._set_window(x0, y0, x1, y1)

    def text(self, s, x, y, font=3, fg=WHITE, bg=BLACK):
        """Draw text using VGA fonts."""
        ft = font1 if font == 1 else (font2 if font == 2 else font3)
        w = ft.WIDTH * len(s)
        h = ft.HEIGHT
        self.fill_rect(x, y, w, h, bg)
        dx = 0
        for ch in s:
            self._draw_char(ft, ch, x + dx, y, fg, bg)
            dx += ft.WIDTH

    def _draw_char(self, ft, ch, x, y, fg, bg):
        """Render a single character glyph."""
        stride = (ft.WIDTH + 7) // 8
        size = stride * ft.HEIGHT
        idx = (ord(ch) - ft.FIRST) * size
        buf = bytearray(ft.WIDTH * ft.HEIGHT * 2)
        bi = 0
        for row in range(ft.HEIGHT):
            for col in range(ft.WIDTH):
                byte = ft.FONT[idx + row * stride + col // 8]
                bit = 7 - (col % 8)
                on = (byte >> bit) & 1
                colr = fg if on else bg
                buf[2 * bi] = (colr >> 8) & 0xFF
                buf[2 * bi + 1] = colr & 0xFF
                bi += 1
        self.blit_buffer(buf, x, y, ft.WIDTH, ft.HEIGHT)

    def scroll(self, top, scroll_h, offset):
        """Set vertical scroll region and offset."""
        self._cmd(_VSCRDEF)
        self._data(struct.pack('>HHH', top, scroll_h, self.height - top - scroll_h))
        self._cmd(_VSCSAD)
        self._data(struct.pack('>H', offset))

