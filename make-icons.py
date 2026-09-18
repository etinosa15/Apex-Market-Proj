"""Rasterise the APEX MARKET "A" mark to PNG.

favicon.svg is the primary icon and will be preferred by any browser that
supports SVG icons, which is all of them since 2020 - but Safari on iOS ignores
rel=icon entirely for home-screen shortcuts, and a handful of crawlers, feed
readers and link-preview services still ask for a PNG. Those two callers are
the whole reason this file exists.

Written against the standard library only: zlib does the compression, struct
does the chunk headers, and the geometry is the same four primitives the SVG
declares, rasterised with 4x4 supersampling for antialiasing. No PIL, no
cairosvg, no build step - consistent with a project that has none.

The PNGs are baked in the light appearance. The SVG swaps its ground with
prefers-color-scheme and these cannot, so they take the paper ground that the
crossbar was designed to be cut from; an icon that is legible on a light tab
and merely unusual on a dark one beats one that is invisible on either.

Run:  py make-icons.py
"""

import struct
import zlib

# --- the mark, in the SVG's own 32-unit viewBox ------------------------------
GROUND = (0xF5, 0xF1, 0xE9)   # --surface, light
BLUE   = (0x0F, 0x5F, 0xC0)   # --accent, light
CLAY   = (0x96, 0x46, 0x1F)   # --warm, light

LEFT_LEG  = [(16, 4), (4, 28), (12, 28)]
RIGHT_LEG = [(16, 4), (28, 28), (20, 28)]
BAR       = (12.5, 19, 7, 3)  # x, y, w, h - drawn in GROUND as a subtractive cut

SS = 4  # supersampling factor per axis


def in_triangle(px, py, tri):
    (ax, ay), (bx, by), (cx, cy) = tri
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if d == 0:
        return False
    a = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
    b = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
    return a >= 0 and b >= 0 and a + b <= 1


def in_rect(px, py, r):
    x, y, w, h = r
    return x <= px < x + w and y <= py < y + h


def sample(px, py):
    """Colour of the mark at a point in viewBox coordinates, drawn in SVG order."""
    c = GROUND
    if in_triangle(px, py, LEFT_LEG):
        c = BLUE
    if in_triangle(px, py, RIGHT_LEG):
        c = CLAY
    if in_rect(px, py, BAR):
        c = GROUND
    return c


def render(size):
    rows = []
    scale = 32.0 / size
    for y in range(size):
        row = bytearray()
        for x in range(size):
            r = g = b = 0
            for sy in range(SS):
                for sx in range(SS):
                    vx = (x + (sx + 0.5) / SS) * scale
                    vy = (y + (sy + 0.5) / SS) * scale
                    c = sample(vx, vy)
                    r += c[0]; g += c[1]; b += c[2]
            n = SS * SS
            row += bytes((r // n, g // n, b // n))
        rows.append(bytes(row))
    return rows


def write_png(path, rows, size):
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = b''.join(b'\x00' + r for r in rows)          # filter type 0 per scanline
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)
    return len(png)


if __name__ == '__main__':
    for path, size in [('favicon-32.png', 32), ('apple-touch-icon.png', 180)]:
        n = write_png(path, render(size), size)
        print('%-22s %3dx%-3d  %5d bytes' % (path, size, size, n))
