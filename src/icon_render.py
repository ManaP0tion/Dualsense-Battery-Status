"""
Tray icon renderer — 64×64 RGBA canvas, OS scales to 16/32 px.
Font resolved through i18n.pil_font() so it matches the active language.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

import i18n

SIZE = 64

# Battery body
BAT_X1, BAT_Y1 = 2,  18
BAT_X2, BAT_Y2 = 52, 46
BAT_R  = 5
INSET  = 3

# Terminal nub
NUB_X1, NUB_Y1 = 53, 26
NUB_X2, NUB_Y2 = 60, 38
NUB_R  = 2

C_OUTLINE = (230, 230, 230, 255)
C_BODY_BG = ( 28,  28,  32, 240)
C_GREEN   = ( 72, 214, 106, 255)
C_YELLOW  = (245, 195,  40, 255)
C_RED     = (220,  55,  55, 255)
C_BLUE    = ( 90, 175, 255, 255)
C_GREY    = (110, 110, 115, 200)
C_TEXT    = (255, 255, 255, 245)
C_SHADOW  = (  0,   0,   0, 160)


def _rrect(draw, xy, radius, fill=None, outline=None, width=1):
    try:
        draw.rounded_rectangle(xy, radius=radius,
                               fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def _fill_color(percent: int, is_charging: bool) -> tuple:
    if is_charging:  return C_BLUE
    if percent > 50: return C_GREEN
    if percent > 20: return C_YELLOW
    return C_RED


def _draw_bolt(draw: ImageDraw.ImageDraw) -> None:
    cx = (BAT_X1 + BAT_X2) // 2
    cy = (BAT_Y1 + BAT_Y2) // 2
    pts = [
        (cx + 5, cy - 10), (cx - 1, cy - 1), (cx + 4,  cy - 1),
        (cx - 5, cy + 10), (cx + 1, cy + 1),  (cx - 4,  cy + 1),
    ]
    draw.polygon(pts, fill=(255, 240, 60, 230))
    for i, p in enumerate(pts):
        draw.line([p, pts[(i + 1) % len(pts)]], fill=(0, 0, 0, 120), width=1)


def render_icon(percent: int, is_charging: bool) -> Image.Image:
    img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    _rrect(draw, [BAT_X1, BAT_Y1, BAT_X2, BAT_Y2],
           radius=BAT_R, fill=C_BODY_BG, outline=C_OUTLINE, width=2)
    _rrect(draw, [NUB_X1, NUB_Y1, NUB_X2, NUB_Y2],
           radius=NUB_R, fill=C_OUTLINE)

    max_fill = BAT_X2 - BAT_X1 - INSET * 2
    fill_w   = int(max_fill * max(0, min(percent, 100)) / 100)
    if fill_w > 0:
        _rrect(draw,
               [BAT_X1 + INSET, BAT_Y1 + INSET,
                BAT_X1 + INSET + fill_w, BAT_Y2 - INSET],
               radius=max(BAT_R - INSET, 1),
               fill=_fill_color(percent, is_charging))

    if is_charging:
        _draw_bolt(draw)
    else:
        label = f"{percent}%"
        fnt   = i18n.pil_font(13)
        bbox  = draw.textbbox((0, 0), label, font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = BAT_X1 + (BAT_X2 - BAT_X1 - tw) // 2
        ty = BAT_Y1 + (BAT_Y2 - BAT_Y1 - th) // 2
        draw.text((tx + 1, ty + 1), label, font=fnt, fill=C_SHADOW)
        draw.text((tx, ty),         label, font=fnt, fill=C_TEXT)

    return img


def render_disconnected() -> Image.Image:
    img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    _rrect(draw, [BAT_X1, BAT_Y1, BAT_X2, BAT_Y2],
           radius=BAT_R, fill=(22, 22, 25, 200), outline=C_GREY, width=2)
    _rrect(draw, [NUB_X1, NUB_Y1, NUB_X2, NUB_Y2],
           radius=NUB_R, fill=C_GREY)

    cx = (BAT_X1 + BAT_X2) // 2
    cy = (BAT_Y1 + BAT_Y2) // 2
    r  = 8
    draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=(200, 55, 55, 220), width=3)
    draw.line([(cx + r, cy - r), (cx - r, cy + r)], fill=(200, 55, 55, 220), width=3)

    return img
