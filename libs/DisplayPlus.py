from machine import Pin, SPI
import st7789
import vga2_8x16 as font_small
import vga2_bold_16x32 as font
import math

color_map = {
    "black": st7789.BLACK,
    "blue": st7789.BLUE,
    "red": st7789.RED,
    "green": st7789.GREEN,
    "cyan": st7789.CYAN,
    "magenta": st7789.MAGENTA,
    "yellow": st7789.YELLOW,
    "white": st7789.WHITE,
}

# BLACK, BLUE, RED, GREEN, CYAN, MAGENTA, YELLOW, and WHITE
# 0x0000, 0x001F, 0xF800, 0x07E0, 0x001F, 0xF800, 0xFFE0, 0xFFFF

class DisplayPlus(st7789.ST7789):
    def __init__(self, rotation=2, options=0, buffer_size=0):
        super().__init__(SPI(1, baudrate=400_000_000, sck=Pin(10), mosi=Pin(11)),
            240,
            320,
            reset=Pin(13, Pin.OUT),
            cs=Pin(15, Pin.OUT),
            dc=Pin(14, Pin.OUT),
            rotation=rotation,
            options=options,
            buffer_size=buffer_size)
        self.display = self
        self.display.init()
        self.font_small = font_small
        self.font_bold = font
        self.BLACK = st7789.BLACK
        self.BLUE = st7789.BLUE
        self.RED = st7789.RED
        self.GREEN = st7789.GREEN
        self.CYAN = st7789.CYAN
        self.MAGENTA = st7789.MAGENTA
        self.YELLOW = st7789.YELLOW
        self.WHITE = st7789.WHITE
    
    def text(self, text, x, y, font=None, fg=None, bg=None):
        if font is None:
            font = self.font_small
        if fg is None:
            fg = st7789.WHITE
        if bg is None:
            bg = st7789.BLACK
        super().text(font, text, x, y, fg, bg)

    def color(self, r, g, b):
        return st7789.color565(r, g, b)

    def draw_circle(self, color, center_x, center_y, r, width=1, start_angle=0, end_angle=360):
        r2 = r + width
        for r in range(r, r2):
            for i in range(start_angle, end_angle):
                dx = center_x + r * math.cos(math.pi/180*i)
                dy = center_y + r * math.sin(math.pi/180*i)
                self.display.pixel(round(dx), round(dy), color)


    def progress_bar(self, center_x, center_y, r, value, min_value, max_value, width=2, color=st7789.GREEN, background_color=st7789.WHITE):
        # Get angle from value
        angle = min(max(value - min_value, 0), max_value - min_value) / (max_value - min_value) * 360
        # Draw progress bar
        self.draw_circle(background_color, center_x, center_y, r, width=width, start_angle=int(angle)-90, end_angle=270)
        self.draw_circle(color, center_x, center_y, r, width=width, start_angle=-90, end_angle=int(angle)-90)

    def draw_poligon(self, center_x, center_y, r, n, bump=1.0, angle_offset=None, color=st7789.WHITE, fill=False):
        buf = []
        angle = 0
        angle_step = 360 / n
        if angle_offset is None:
            angle_offset = angle_step / 2 if n % 2 == 0 else 90
        for i in range(n + 1):
            dx = center_x + r * math.cos(math.pi/180*(angle-angle_offset))
            dy = center_y + r * math.sin(math.pi/180*(angle-angle_offset))
            angle += angle_step
            ddx = center_x + r * math.cos(math.pi/180*(angle-angle_offset))
            ddy = center_y + r * math.sin(math.pi/180*(angle-angle_offset))

            mid_x = dx + (ddx - dx) / 2
            mid_y = dy + (ddy - dy) / 2

            bdx = center_x + (mid_x - center_x) * bump
            bdy = center_y + (mid_y - center_y) * bump

            buf.append((round(dx), round(dy)))
            buf.append((round(bdx), round(bdy)))

        if fill:
            self.fill_polygon(buf, 0, 0, color)
        else:
            self.polygon(buf, 0, 0, color)

    def draw_logo(self, x=120, y=100, r=80):
        super().fill(st7789.WHITE)
        self.draw_poligon(x, y, r, 8, bump=0.7, fill=True, color=st7789.BLACK)
        self.draw_poligon(x, y, r * 0.7, 4, bump=0.3, fill=True, color=st7789.WHITE, angle_offset=0)
        self.text("Artisan", x - r, y + r, font=font, fg=st7789.BLACK, bg=st7789.WHITE)
        self.text("Education", x - r, y + r + 32, font=font, fg=st7789.BLACK, bg=st7789.WHITE)
        self.text("artisan.education", 100, 300, fg=st7789.BLACK, bg=st7789.WHITE)
