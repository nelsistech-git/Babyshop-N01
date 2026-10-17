# -*- coding: utf-8 -*-
"""Tiny dependency-free PDF writer used for the fictitious supporting documents."""


def _esc(text):
    return (str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)'))


def make_pdf(title, lines=()):
    """Return the bytes of a one-page PDF. The text is always unique per call, so the
    attachment checksums differ (the commercial module rejects duplicate files)."""
    content = 'BT /F1 16 Tf 50 790 Td (%s) Tj /F1 11 Tf' % _esc(title)
    for line in lines:
        content += ' 0 -20 Td (%s) Tj' % _esc(line)
    content += ' 0 -40 Td (FICTITIOUS DEMO DOCUMENT - NOT A REAL RECORD) Tj ET'
    stream = content.encode('latin-1', 'replace')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
        b'/Resources << /Font << /F1 5 0 R >> >> >>',
        b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    out = bytearray(b'%PDF-1.4\n')
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % index + obj + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n' % (len(objects) + 1)
    out += b'0000000000 65535 f \n'
    for offset in offsets:
        out += b'%010d 00000 n \n' % offset
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, xref)
    return bytes(out)
