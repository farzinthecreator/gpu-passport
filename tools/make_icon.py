"""Draws the GPU Passport icon (a graphics card with a green check badge) and writes icon.png + icon.ico.

Run from the repo root: python tools/make_icon.py
Pure standard library: shapes are tested per sub-pixel (4x4 supersampling) for smooth edges.
"""
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLUE_TOP, BLUE_BOTTOM = (42, 106, 224), (24, 76, 180)
WHITE, GREEN = (255, 255, 255), (30, 158, 90)


def rounded_rect(x, y, x0, y0, x1, y1, r):
    cx, cy = min(max(x, x0 + r), x1 - r), min(max(y, y0 + r), y1 - r)
    return x0 <= x <= x1 and y0 <= y <= y1 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def near_segment(x, y, a, b, width):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)))
    return (x - a[0] - t * dx) ** 2 + (y - a[1] - t * dy) ** 2 <= (width / 2) ** 2


def color_at(x, y):
    """Painter's order, coordinates 0..1. Returns (r, g, b) or None for transparent."""
    badge = (0.735, 0.725)
    if circle(x, y, *badge, 0.205):  # badge with a white ring that separates it from the card
        if not circle(x, y, *badge, 0.165):
            return WHITE
        if near_segment(x, y, (0.665, 0.728), (0.718, 0.780), 0.055) or near_segment(x, y, (0.718, 0.780), (0.810, 0.672), 0.055):
            return WHITE
        return GREEN
    if not rounded_rect(x, y, 0.0, 0.0, 1.0, 1.0, 0.22):
        return None
    background = tuple(round(a + (b - a) * y) for a, b in zip(BLUE_TOP, BLUE_BOTTOM))
    if rounded_rect(x, y, 0.13, 0.27, 0.175, 0.73, 0.012):  # mounting bracket
        return WHITE
    if 0.30 <= x <= 0.62 and 0.655 <= y <= 0.715 and int((x - 0.30) / 0.032) % 2 == 0:  # PCIe contacts
        return WHITE
    if rounded_rect(x, y, 0.19, 0.30, 0.86, 0.665, 0.045):  # card body with two fans
        for fan_x in (0.36, 0.665):
            if circle(x, y, fan_x, 0.4825, 0.125):
                if circle(x, y, fan_x, 0.4825, 0.035):
                    return WHITE  # hub
                angle = math.atan2(y - 0.4825, x - fan_x)
                return WHITE if (angle * 7 / math.pi) % 2 < 0.55 and not circle(x, y, fan_x, 0.4825, 0.055) else background
        return WHITE
    return background


def render(size, samples=4):
    pixels = bytearray()
    for py in range(size):
        pixels.append(0)  # PNG filter type: none
        for px in range(size):
            r = g = b = a = 0
            for sy in range(samples):
                for sx in range(samples):
                    c = color_at((px + (sx + 0.5) / samples) / size, (py + (sy + 0.5) / samples) / size)
                    if c:
                        r, g, b, a = r + c[0], g + c[1], b + c[2], a + 1
            n = samples * samples
            pixels += bytes((r // a, g // a, b // a, round(255 * a / n)) if a else (0, 0, 0, 0))
    return pixels


def png(size):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(render(size)), 9)) + chunk(b"IEND", b"")


def ico(images):
    """ICO file holding PNG images (supported since Windows Vista)."""
    out = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    for size, data in images:
        out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return out + b"".join(data for _, data in images)


if __name__ == "__main__":
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [(s, png(s)) for s in sizes]
    (ROOT / "icon.ico").write_bytes(ico(images))
    (ROOT / "icon.png").write_bytes(dict(images)[256])
    print(f"wrote icon.ico ({', '.join(map(str, sizes))} px) and icon.png (256 px)")
