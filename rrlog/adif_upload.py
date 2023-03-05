from django.db import transaction
from rrlog import adif_io, country
from rrlog.utils import lower, upper

q_insert_qso = """insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, submode, rsttx, rstrx, gridsquare, contest, upload, adif)
values (date_trunc('minute', %s), %s, %s, %s, %s, coalesce(%s::band, %s::numeric::band), %s, major_mode(%s, %s), %s, %s, %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator = excluded.operator,
dxcc = excluded.dxcc,
band = excluded.band,
freq = excluded.freq,
major_mode = excluded.major_mode,
mode = excluded.mode,
submode = excluded.submode,
rsttx = excluded.rsttx,
rstrx = excluded.rstrx,
gridsquare = excluded.gridsquare,
contest = excluded.contest,
upload = excluded.upload,
adif = excluded.adif
"""

def adif_upload(cursor, content, station_callsign, operator, contest, upload_id):
    with transaction.atomic():
        qsos, adif_headers = adif_io.read_from_string(content)
        upload_start, upload_stop = None, None

        for qso in qsos:
            start = adif_io.time_on(qso)
            upload_start = min(upload_start, start) if upload_start else start
            upload_stop = max(upload_stop, start) if upload_stop else start

            qso_station = qso.get('STATION_CALLSIGN') or station_callsign \
                    or qso.get('OPERATOR') or operator
            qso_operator = qso.get('OPERATOR') or operator \
                    or qso.get('STATION_CALLSIGN') or station_callsign
            if qso_station == qso_operator:
                qso_operator = None

            if not station_callsign and not operator:
                raise Exception(f"{start} {qso.get('CALL')}: QSO without STATION_CALLSIGN and OPERATOR found in log, set station and/or operator in upload form")

            call = upper(qso.get('CALL'))
            if 'DXCC' in qso and qso.get('DXCC').strip() != '':
                dxcc = qso.get('DXCC')
            else:
                dxcc = country.lookup(call, start)

            tx_rpts = [upper(qso.get('RST_SENT')), upper(qso.get('STX')), upper(qso.get('STX_STRING'))]
            rsttx = ' '.join(filter(None, tx_rpts)) or None
            rx_rpts = [upper(qso.get('RST_RCVD')), upper(qso.get('SRX')), upper(qso.get('SRX_STRING'))]
            rstrx = ' '.join(filter(None, rx_rpts)) or None

            freq = qso.get('FREQ')
            mode = upper(qso.get('MODE'))
            submode = upper(qso.get('SUBMODE'))

            gridsquare = qso['GRIDSQUARE'][:4].upper() \
                if 'GRIDSQUARE' in qso else None

            cursor.execute(q_insert_qso,
                           [start,
                            qso_station,
                            qso_operator,
                            call,
                            dxcc,
                            lower(qso.get('BAND')),
                            freq, freq,
                            mode, submode, mode, submode,
                            rsttx,
                            rstrx,
                            gridsquare,
                            qso.get('CONTEST_ID') or contest,
                            upload_id,
                            qso,
                            ])
        cursor.execute("update upload set qsos = %s, start = %s, stop = %s where id = %s", [len(qsos), upload_start, upload_stop, upload_id])

    return len(qsos)
