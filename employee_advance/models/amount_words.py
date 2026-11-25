# -*- coding: utf-8 -*-
"""Amount in words (Bangladeshi numbering) for the Advance Claim Sheet."""


_ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
         'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen',
         'Eighteen', 'Nineteen']
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _below_hundred(n):
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + ' ' + _ONES[n % 10]).strip()


def _below_thousand(n):
    words = []
    if n >= 100:
        words.append(_ONES[n // 100] + ' Hundred')
        n %= 100
    if n:
        words.append(_below_hundred(n))
    return ' '.join(words)


def _int_to_words_bd(n):
    """Bangladeshi numbering: Thousand, Lakh, Crore."""
    if n == 0:
        return 'Zero'
    parts = []
    for unit, size in (('Crore', 10000000), ('Lakh', 100000), ('Thousand', 1000)):
        if n >= size:
            parts.append(_int_to_words_bd(n // size) + ' ' + unit)
            n %= size
    if n:
        parts.append(_below_thousand(n))
    return ' '.join(parts)


def _amount_to_words_bdt(amount):
    """1250.5 -> 'One Thousand Two Hundred Fifty Taka and Fifty Paisa Only'"""
    amount = round(amount or 0.0, 2)
    taka = int(amount)
    paisa = int(round((amount - taka) * 100))
    words = _int_to_words_bd(taka) + ' Taka'
    if paisa:
        words += ' and ' + _int_to_words_bd(paisa) + ' Paisa'
    return words + ' Only'
