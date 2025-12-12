#!/usr/bin/python3

import pyhamtools.frequency
import re
from datetime import datetime, timezone

# QSO:  3799 PH 1999-03-06 0711 HC8N           59 700    W1AW           59 CT     0
# QSO: 21034 CW 2024-05-01 1900 DK8ZZ         ZIK        DL    N1LN          BRUCE      1141
# QSO:  7044 RY 2024-04-28 1701 DF5BX             001    DD7UW             001
# QSO: 3577 DG 2024-04-29 1902 DL3KWF       +14  JO64 OK2USM       +07  JN89
# QSO: 3577 DG 2024-04-29 1903 DL3KWF       +13  JO64 M0NPT        +11      

def parse_qso(fields, call2_index, has_rst, has_trx):
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

    # fields 0-4 are fixed, the rest varies greatly
    data = {
        'freq': freq,
        'band': band_mode['band'],
        'mode': fields[1],
        'ts': ts,
        'station_callsign': fields[4],
    }

    if has_trx:
        trx = int(fields.pop())

    if has_rst:
        data['rsttx'] = fields[5]
        data['extx'] = ' '.join(fields[6:call2_index])
        data['call'] = fields[call2_index]
        data['rstrx'] = fields[call2_index+1]
        data['exrx'] = ' '.join(fields[call2_index+2:])
    else:
        data['rsttx'] = None
        data['extx'] = ' '.join(fields[5:call2_index])
        data['call'] = fields[call2_index]
        data['rstrx'] = None
        data['exrx'] = ' '.join(fields[call2_index+1:])

    if has_trx:
        data['trx'] = trx

    return data

def is_report(field):
    return re.match(r'5[1-9]9?$|[+-][0-9][0-9]$', field) # 599 59 +10 -08

def parse(cbr):
    in_data = False
    data = {'qsos': []}
    qsos = []
    x_qsos = []
    lengths = set()

    for line in cbr.splitlines():
        if line.strip() == "": continue # skip over blank lines
        field, sep, value = line.partition(':')
        if sep == '':
            if in_data:
                raise Exception('Malformed line without colon in data section found')
            else:
                continue
        field, value = field.upper(), value.strip()
        if value == "": continue # skip empty fields

        if field == 'START-OF-LOG':
            in_data = True
        elif field == 'END-OF-LOG':
            break
        elif field == 'QSO':
            qso = value.split()
            qsos.append(qso)
            lengths.add(len(qso))
        elif field == 'X-QSO':
            x_qso = value.split()
            x_qsos.append(x_qso)
            lengths.add(len(x_qso))
        if field in data:
            data[field] += '\n' + value
        else:
            data[field] = value

    # check if the first column after the station call looks like a report
    # check if the last column is a transceiver number
    has_rst = True
    has_trx = True
    for qso in qsos:
        if not is_report(qso[5]):
            has_rst = False
        if not qso[-1] in ('0', '1'):
            has_trx = False

    call1_index = 4
    if len(lengths) == 1: # all lines have same number of fields
        length = lengths.pop() - has_trx
        # if the length is even, assume boths sides have the same number of fields
        if length % 2 == 0:
            call2_index = 4 + int((length - 4) / 2)
        else:
            # the length is odd, see if we can find a report on the right side
            i = 4 + int((length - 3) / 2)
            if is_report(qsos[0][i+1]):
                call2_index = i
            elif is_report(qsos[0][i]):
                call2_index = i - 1
            else:
                raise Exception("Cannot parse Cabrillo log; QSO lines have an odd number of elements and I could not spot a report column")
    else: # hope we can find a report
        length = min(lengths)
        length = lengths.pop() - has_trx
        i = 4 + int((length - 3) / 2)
        if is_report(qsos[0][i+1]):
            call2_index = i
        elif is_report(qsos[0][i]):
            call2_index = i - 1
        else:
            raise Exception("Cannot parse Cabrillo log; QSO lines have multiple different numbers of elements and I could not spot a report column")

    for qso in qsos:
        data['qsos'].append(parse_qso(qso, call2_index=call2_index, has_rst=has_rst, has_trx=has_trx))
    if x_qsos:
        data['x-qsos'] = []
        for x_qso in x_qsos:
            data['x-qsos'].append(parse_qso(x_qso, call2_index=call2_index, has_rst=has_rst, has_trx=has_trx))

    return data

if __name__ == '__main__':
    import sys
    print(parse(sys.stdin.read()))
