from django.db import transaction
import re
from rrlog import cabrillo, country
from rrlog.utils import upper

def cabrillo_upload(cursor, content, upload_id):
    cbr = cabrillo.parse(content)
    qsos = cbr['qsos']
    upload_start, upload_stop = None, None

    if 'CALLSIGN' not in cbr:
        raise Exception("Cabrillo log is missing the CALLSIGN header")
    station_callsign = cbr.get('CALLSIGN').upper()
    operators = upper(cbr.get('OPERATORS'))
    operator = None
    # if there is a single operator specified in the Cabrillo file, use it
    if operators and re.match(r'[\w\d/]+$', operators) and station_callsign != operators:
        operator = operators

    contest = cbr.get('CONTEST')

    with transaction.atomic():
        for qso in qsos:
            start = qso['ts']
            upload_start = min(upload_start, start) if upload_start else start
            upload_stop = max(upload_stop, start) if upload_stop else start

            qso_station = qso['station_callsign'].upper()
            if qso_station != station_callsign:
                raise Exception(f"Cabrillo header CALLSIGN {station_callsign} does not match QSO station callsign {qso_station}")

            call = qso['call'].upper()
            dxcc = country.lookup(call, start)

            freq = qso['freq'] / 1000
            if qso['band'] >= 2:
                band = str(int(qso['band'])) + 'm'
            elif qso['band'] == 0.053:
                band = '6cm'
            elif qso['band'] >= 0.0125:
                band = str(int(qso['band'] * 100.0)) + 'cm'
            else:
                raise Exception(f"Band {qso['band']} is not supported yet, please contact DF7CB")

            major_mode = qso['mode'].upper()
            submode = None
            # CW
            if major_mode == 'CW':
                mode = 'CW'
            # PHONE
            elif major_mode == 'PH':
                major_mode = 'PHONE'
                mode = 'SSB'
            elif major_mode == 'FM':
                major_mode = 'PHONE'
                mode = 'FM'
            elif major_mode == 'AM':
                major_mode = 'PHONE'
                mode = 'AM'
            # DIGI
            elif major_mode == 'RY':
                major_mode = 'DIGI'
                mode = 'RTTY'
            elif major_mode in ('PS', 'PK', 'PM', 'PO'):
                # https://www.rdrclub.ru/index.php/russian-ww-psk-contest/49-rus-ww-psk-rules
                # BPSK31 - PS, BPSK63 - PM, BPSK125 - PO
                # RSGB handles it differently: https://www.rsgbcc.org/hf/rules/2025/rautumn.shtml
                # RTTY = RY, PSK63 = PS, SSB = PH, CW = CW
                if major_mode == 'PS':
                    submode = 'PSK31'
                elif major_mode == 'PM':
                    submode = 'PSK63'
                elif major_mode == 'PO':
                    submode = 'PSK125'
                major_mode = 'DIGI'
                mode = 'PSK'
            elif major_mode == 'DG':
                major_mode = 'DIGI'
                mode = None
            # FT8
            elif major_mode == 'FT':
                major_mode = 'FT8'
                mode = None
            else:
                raise Exception(f"Cabillo mode {major_mode} is not supported yet, please contact DF7CB")

            cursor.execute("""\
insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, submode, rsttx, extx, rstrx, exrx, contest, upload)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator = coalesce(excluded.operator, log.operator),
dxcc =     coalesce(excluded.dxcc, log.dxcc),
freq =     coalesce(excluded.freq, log.freq),
mode =     coalesce(excluded.mode, log.mode),
submode =  coalesce(excluded.submode, log.submode),
rsttx =    excluded.rsttx,
extx =     excluded.extx,
rstrx =    excluded.rstrx,
exrx =     excluded.exrx,
contest =  excluded.contest,
upload =   excluded.upload
""",
                           [start,
                            station_callsign, operator,
                            call,
                            dxcc,
                            band, freq,
                            major_mode, mode, submode,
                            qso['rsttx'], qso['extx'],
                            qso['rstrx'], qso['exrx'],
                            contest,
                            upload_id,
                            ])

        cursor.execute("""update upload set
qsos = %s,
start = %s,
stop = %s,
contest = %s,
station_callsign = %s,
operator = %s,
operators = upper(%s),
club = %s,
category_operator = %s,
category_assisted = %s,
category_band = %s,
category_mode = %s,
category_overlay = %s,
category_power = %s,
category_station = %s,
category_time = %s,
category_transmitter = %s,
location = %s,
grid_locator = %s,
soapbox = %s,
claimed_score = %s,
exchange = %s
where id = %s""",
                       [len(qsos),
                        upload_start,
                        upload_stop,
                        contest,
                        station_callsign,
                        operator, # only set when there is a single operator
                        cbr.get('OPERATORS') or None, # one or more operators
                        cbr.get('CLUB') or None,
                        cbr.get('CATEGORY-OPERATOR') or None,
                        cbr.get('CATEGORY-ASSISTED') or None,
                        cbr.get('CATEGORY-BAND') or None,
                        cbr.get('CATEGORY-MODE') or None,
                        cbr.get('CATEGORY-OVERLAY') or None,
                        cbr.get('CATEGORY-POWER') or None,
                        cbr.get('CATEGORY-STATION') or None,
                        cbr.get('CATEGORY-TIME') or None,
                        cbr.get('CATEGORY-TRANSMITTER') or None,
                        cbr.get('LOCATION') or None,
                        cbr.get('GRID-LOCATOR') or None,
                        cbr.get('SOAPBOX') or None,
                        cbr.get('CLAIMED-SCORE') or None,
                        qsos[0]['extx'] or None if len(qsos) > 0 else None,
                        upload_id])

    return len(qsos)
