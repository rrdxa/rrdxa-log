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
