from django.db import transaction
import re
from rrlog import edi, country
from rrlog.utils import upper

# EDI mode code -> (major_mode, mode, submode), per the mode table in the
# EDI spec:
#   0 none, 1 SSB, 2 CW, 3 SSB-TX/CW-RX, 4 CW-TX/SSB-RX, 5 AM, 6 FM,
#   7 RTTY, 8 SSTV, 9 ATV
# The logbook has one mode per QSO, so the cross-mode codes 3 and 4 are
# filed under the mode that was *transmitted*; 9 (ATV) goes under DIGI
# together with the other image modes.
modes = {
    '1': ('PHONE', 'SSB', None),
    '2': ('CW', 'CW', None),
    '3': ('PHONE', 'SSB', None),
    '4': ('CW', 'CW', None),
    '5': ('PHONE', 'AM', None),
    '6': ('PHONE', 'FM', None),
    '7': ('DIGI', 'RTTY', None),
    '8': ('DIGI', 'SSTV', None),
    '9': ('DIGI', 'ATV', None),
}

# EDI PBand -> rrdxa.band, per the frequency table in the spec. The EDI
# value is a band name, not a frequency, so this replaces the usual
# freq -> band lookup.
bands = {
    '50 MHZ': '6m',
    '70 MHZ': '4m',
    '144 MHZ': '2m',
    '145 MHZ': '2m',
    '432 MHZ': '70cm',
    '435 MHZ': '70cm',
    '1.2 GHZ': '23cm',
    '1.3 GHZ': '23cm',
    '2.3 GHZ': '13cm',
    '3.4 GHZ': '9cm',
    '5.7 GHZ': '6cm',
    '10 GHZ': '3cm',
    '24 GHZ': '1.25cm',
    '47 GHZ': '6mm',
    '76 GHZ': '4mm',
    '120 GHZ': '2.5mm',
    '144 GHZ': '2mm',
    '248 GHZ': '1mm',
}

q_insert_qso = """\
insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, submode, rsttx, extx, rstrx, exrx, gridsquare, contest, upload)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator =   coalesce(excluded.operator, log.operator),
dxcc =       coalesce(excluded.dxcc, log.dxcc),
freq =       coalesce(excluded.freq, log.freq),
mode =       coalesce(excluded.mode, log.mode),
submode =    coalesce(excluded.submode, log.submode),
rsttx =      excluded.rsttx,
extx =       excluded.extx,
rstrx =      excluded.rstrx,
exrx =       excluded.exrx,
gridsquare = coalesce(excluded.gridsquare, log.gridsquare),
contest =    excluded.contest,
upload =     excluded.upload
"""

q_update_upload = """\
update upload set
qsos = %s,
start = %s,
stop = %s,
contest = %s,
station_callsign = %s,
operator = %s,
operators = %s,
club = %s,
category_operator = %s,
category_band = %s,
grid_locator = %s,
soapbox = %s,
claimed_score = %s,
exchange = %s
where id = %s
"""


def band_from_pband(pband):
    # The spec writes "1,3 GHz" (German decimal comma); accept both.
    key = upper(pband or '').strip().replace(',', '.')
    if key not in bands:
        raise Exception(f"EDI band '{pband}' is not supported yet, please contact DF7CB")
    return bands[key]


def _int(value):
    value = (value or '').strip()
    return int(value) if re.match(r'^\d+$', value) else None


def edi_upload(cursor, content, upload_id):
    data = edi.parse(content)
    qsos = data['qsos']
    upload_start, upload_stop = None, None

    if 'PCALL' not in data:
        raise Exception("EDI log is missing the PCall header")
    station_callsign = upper(data['PCALL']).strip()
    if not station_callsign:
        raise Exception("EDI log is missing the PCall header")
    band = band_from_pband(data.get('PBAND'))

    contest = data.get('TNAME') or None

    # MOpe1/MOpe2 are semicolon-separated lists of operators. Record the
    # full list, and additionally set the single-operator column when the
    # log names exactly one operator other than the station callsign.
    operators = ';'.join(filter(None, [data.get('MOPE1', ''), data.get('MOPE2', '')]))
    operators = upper(operators) or None
    operator = None
    op_list = [op for op in re.split(r'[;,\s]+', operators or '') if op]
    if len(op_list) == 1 and op_list[0] != station_callsign:
        operator = op_list[0]

    with transaction.atomic():
        for qso in qsos:
            start = qso['ts']
            upload_start = min(upload_start, start) if upload_start else start
            upload_stop = max(upload_stop, start) if upload_stop else start

            call = qso['call']
            dxcc = country.lookup(call, start)
            major_mode, mode, submode = modes.get(qso['mode'], ('unknown', None, None))

            cursor.execute(q_insert_qso,
                           [start,
                            station_callsign, operator,
                            call,
                            dxcc,
                            band, None,  # EDI has no per-QSO frequency
                            major_mode, mode, submode,
                            qso['rsttx'] or None,
                            qso['extx'] or None,
                            qso['rstrx'] or None,
                            qso['exrx'] or None,
                            qso['wwl'] or None,
                            contest,
                            upload_id,
                            ])

        cursor.execute(q_update_upload,
                       [len(qsos),
                        upload_start,
                        upload_stop,
                        contest,
                        station_callsign,
                        operator,
                        operators,
                        data.get('PCLUB') or None,
                        data.get('PSECT') or None,
                        data.get('PBAND') or None,
                        data.get('PWWLO') or None,
                        data.get('REMARKS') or None,
                        _int(data.get('CTOSC')),
                        data.get('PEXCH') or None,
                        upload_id])

    return len(qsos)
