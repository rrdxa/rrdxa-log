#!/usr/bin/python3

import pyhamtools.frequency
import re
from datetime import datetime, timezone

# QSO:  3799 PH 1999-03-06 0711 HC8N           59 700    W1AW           59 CT     0
def parse_qso(qso):
    fields = qso.split()
    trx = None
    freq = fields[0]
    if freq in ('50', '70', '144', '222', '432', '902'):
        freq = int(freq) * 1000
    elif re.match(r'\d+$', freq):
        freq = int(freq)
    elif re.match(r'\d+(\.\d+)M$', freq): # non-standard
         freq = int(float(freq[:-1]) * 1000)
    elif re.match(r'\d+(\.\d+)G$', freq):
         freq = int(float(freq[:-1]) * 1000000)
    else:
        raise Exception(f"Cannot determine band from frequency '{freq}'")
    band_mode = pyhamtools.frequency.freq_to_band(freq)
    ts = datetime.strptime(fields[2] + ' ' + fields[3], '%Y-%m-%d %H%M').replace(tzinfo=timezone.utc)

    data = {
        'freq': freq,
        'band': band_mode['band'],
        'mode': fields[1],
        'ts': ts,
        'station_callsign': fields[4],
        'rsttx': fields[5],
        'extx': fields[6],
    }

    # if there's a 0 or 1 in the last column, it's the transceiver number
    if fields[-1] in ('0', '1'):
        trx = int(fields.pop())

    # ['W1AW', '59', 'CT']
    # if the 2nd field in rest is all-numeric, it's the report, else there was a 2nd part of extx
    rest = fields[7:]
    if re.match(r'\d+$', rest[1]):
        data['call'] = rest[0]
        data['rstrx'] = rest[1]
        data['exrx'] = ' '.join(rest[2:])
    else:
        data['extx'] += ' ' + rest[0]
        data['call'] = rest[1]
        data['rstrx'] = rest[2]
        data['exrx'] = ' '.join(rest[3:])

    if trx != None:
        data['trx'] = trx
    return data

def parse(cbr):
    in_data = False
    data = {'qsos': []}

    for line in cbr.splitlines():
        field, sep, value = line.partition(':')
        if sep == None:
            if in_data:
                raise Exception('Malformed line without colon in data section found')
            else:
                continue
        field, value = field.upper(), value.strip()

        if field == 'START-OF-LOG':
            in_data = True
        elif field == 'END-OF-LOG':
            break
        elif field == 'QSO':
            data['qsos'].append(parse_qso(value))
        elif field == 'X-QSO':
            if 'X-QSO' not in data:
                data['X-QSO'] = []
            data['x-qsos'].append(parse_qso(value))
        if field in data:
            data[field] += '\n' + value
        else:
            data[field] = value

    return data

if __name__ == '__main__':
    import sys
    print(parse(sys.stdin.read()))
