from collections import namedtuple

def namedtuplefetchall(cursor):
    "Return all rows from a cursor as a namedtuple"
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]

def lower(text):
    if text == None:
        return None
    return text.lower()

def upper(text):
    if text == None:
        return None
    return text.upper()

def concat(strings):
    return ' '.join(filter(None, strings)) or None

all_bands = [
    '2190m',
    '630m',
    '560m',
    '160m',
    '80m',
    '60m',
    '40m',
    '30m',
    '20m',
    '17m',
    '15m',
    '12m',
    '10m',
    '8m',
    '6m',
    '5m',
    '4m',
    '2m',
    '1.25m',
    '70cm',
    '33cm',
    '23cm',
    '13cm',
    '9cm',
    '6cm',
    '3cm',
    '1.25cm',
    '6mm',
    '4mm',
    '2.5mm',
    '2mm',
    '1mm',
]

def band_sort(bands):
    ret = []
    for band in all_bands:
        if band in bands:
            ret.append(band)
    return ret
