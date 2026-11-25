import base64
import io
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

MAX_SIDE = 1600
JPEG_QUALITY = 75


def normalize_bill_image(raw):
    """Return (jpeg_bytes, dhash_hex, width, height). Applies EXIF rotation, strips metadata,
    resizes to max 1600 px and re-encodes as JPEG q75 so every bill has a uniform, small format."""
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ('RGB', 'L'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode in ('RGBA', 'LA'):
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img.convert('RGB'))
        img = bg
    elif img.mode == 'L':
        img = img.convert('RGB')
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    w, h = img.size
    # difference hash (9x8) for duplicate-bill detection
    g = img.convert('L').resize((9, 8), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (1 if px[row * 9 + col] > px[row * 9 + col + 1] else 0)
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=JPEG_QUALITY, optimize=True)
    return out.getvalue(), '%016x' % bits, w, h


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    nl_bill_hash = fields.Char(string='Bill Image Hash', index=True, copy=False)
    nl_captured_at = fields.Datetime(string='Photo Taken (phone time)')
    nl_capture_lat = fields.Float(digits=(10, 7))
    nl_capture_lng = fields.Float(digits=(10, 7))
