"""
Generate assets/app_icon.ico  (16/32/48/64/128/256 px multi-size)
and  assets/app_icon.png      (256 px, for reference).

Run once before packaging:
    python generate_app_icon.py
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)

ICO_SIZES = [16, 32, 48, 64, 128, 256]


# ── Colour palette ─────────────────────────────────────────────────────────────
BG_DARK    = ( 12,  16,  36, 255)   # deep navy
BG_EDGE    = ( 22,  32,  70, 255)   # slightly lighter edge for gradient feel
OUTLINE    = (220, 225, 255, 255)   # near-white with a blue tint
FILL_GREEN = ( 72, 214, 106, 255)   # same as tray icon
BOLT_YELLOW= (255, 235,  60, 230)

# PlayStation button accent colours
PS_TRIANGLE = ( 50, 195, 180, 200)
PS_CIRCLE   = (230,  70,  95, 200)
PS_CROSS    = ( 90, 170, 230, 200)
PS_SQUARE   = (210,  90, 190, 200)


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _rrect(draw: ImageDraw.ImageDraw, xy, radius: int,
           fill=None, outline=None, width: int = 1) -> None:
    try:
        draw.rounded_rectangle(xy, radius=radius,
                               fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf",
                 "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _ps_triangle(draw: ImageDraw.ImageDraw,
                 cx: int, cy: int, r: int) -> None:
    """Equilateral triangle (PlayStation △)."""
    pts = [
        (cx,             cy - r),
        (cx + int(r * math.sin(math.radians(120))),
         cy + int(r * math.cos(math.radians(120)))),
        (cx + int(r * math.sin(math.radians(240))),
         cy + int(r * math.cos(math.radians(240)))),
    ]
    draw.polygon(pts, fill=PS_TRIANGLE)


def _ps_circle(draw: ImageDraw.ImageDraw,
               cx: int, cy: int, r: int) -> None:
    lw = max(2, r // 5)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 outline=PS_CIRCLE, width=lw)


def _ps_cross(draw: ImageDraw.ImageDraw,
              cx: int, cy: int, r: int) -> None:
    lw = max(2, r // 4)
    draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=PS_CROSS, width=lw)
    draw.line([(cx + r, cy - r), (cx - r, cy + r)], fill=PS_CROSS, width=lw)


def _ps_square(draw: ImageDraw.ImageDraw,
               cx: int, cy: int, r: int) -> None:
    lw = max(2, r // 5)
    draw.rectangle([cx - r, cy - r, cx + r, cy + r],
                   outline=PS_SQUARE, width=lw)


# ── Main icon builder ──────────────────────────────────────────────────────────

def build_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size  # shorthand

    # ── Background: dark rounded square ───────────────────────────────────────
    pad = max(1, s // 20)
    bg_r = s // 6
    # Slightly lighter inner fill to fake a soft gradient
    _rrect(draw, [pad, pad, s - pad, s - pad],
           radius=bg_r, fill=BG_EDGE)
    inner = s // 14
    _rrect(draw, [pad + inner, pad + inner,
                  s - pad - inner, s - pad - inner],
           radius=max(bg_r - inner, 2), fill=BG_DARK)

    # ── PS button symbols (four corners, decorative) ───────────────────────────
    # Only draw when the icon is large enough to show them
    if size >= 48:
        sym_r  = max(3, s // 18)
        sym_off = s // 5
        _ps_triangle(draw, s - sym_off, sym_off,     sym_r)
        _ps_circle  (draw, s - sym_off, s - sym_off, sym_r)
        _ps_cross   (draw, sym_off,     s - sym_off, sym_r)
        _ps_square  (draw, sym_off,     sym_off,     sym_r)

    # ── Battery body ──────────────────────────────────────────────────────────
    bpad   = s // 7
    bx1    = bpad
    by1    = s // 3
    bx2    = s - bpad - s // 16    # leave room for nub
    by2    = s - s // 3
    b_r    = max(3, s // 20)
    border = max(2, s // 48)

    _rrect(draw, [bx1, by1, bx2, by2],
           radius=b_r,
           fill=(255, 255, 255, 18),
           outline=OUTLINE,
           width=border)

    # Nub
    nub_w = s // 16
    ny1   = (by1 + by2) // 2 - s // 16
    ny2   = (by1 + by2) // 2 + s // 16
    _rrect(draw, [bx2, ny1, bx2 + nub_w, ny2],
           radius=max(1, s // 48),
           fill=OUTLINE)

    # Green fill (100% charged — it's the branding/app icon)
    inset = border + max(1, s // 56)
    _rrect(draw,
           [bx1 + inset, by1 + inset, bx2 - inset, by2 - inset],
           radius=max(b_r - inset, 1),
           fill=FILL_GREEN)

    # ── Percentage label centred in the battery ────────────────────────────────
    if size >= 32:
        bat_h  = by2 - by1
        fnt_sz = max(8, bat_h * 38 // 100)
        fnt    = _font(fnt_sz)
        label  = "100%"
        bbox   = draw.textbbox((0, 0), label, font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = bx1 + (bx2 - bx1 - tw) // 2
        ty = by1 + (by2 - by1 - th) // 2
        # shadow
        draw.text((tx + 1, ty + 1), label, font=fnt,
                  fill=(0, 0, 0, 160))
        draw.text((tx, ty), label, font=fnt,
                  fill=(255, 255, 255, 245))

    # ── "DualSense Battery" subtitle ──────────────────────────────────────────
    if size >= 128:
        sub_fnt = _font(max(8, s // 18))
        sub     = "DualSense Battery"
        sbbox   = draw.textbbox((0, 0), sub, font=sub_fnt)
        sw = sbbox[2] - sbbox[0]
        sx = (s - sw) // 2
        sy = by2 + max(4, s // 28)
        draw.text((sx + 1, sy + 1), sub, font=sub_fnt,
                  fill=(0, 0, 0, 130))
        draw.text((sx, sy), sub, font=sub_fnt,
                  fill=(180, 200, 255, 210))

    return img


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    base = build_icon(256)
    base.save(ASSETS / "app_icon.png")
    print(f"Saved app_icon.png  ({base.size})")

    frames = []
    for sz in ICO_SIZES:
        frame = build_icon(sz) if sz >= 64 else base.resize(
            (sz, sz), Image.LANCZOS
        )
        frames.append(frame)
        print(f"  prepared {sz}×{sz}")

    # Save multi-size .ico
    ico_path = ASSETS / "app_icon.ico"
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[1:],
    )
    print(f"Saved app_icon.ico  → {ico_path}")


if __name__ == "__main__":
    main()
