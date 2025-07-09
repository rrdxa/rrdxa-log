import json
from django.db import transaction
from rrlog import adif_io, country
from rrlog.utils import lower, upper, concat

q_insert_qso = """insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, submode, rsttx, extx, rstrx, exrx, gridsquare, contest, upload, adif)
values (date_trunc('minute', %s), %s, %s, %s, %s, coalesce(%s::band, %s::numeric::band), %s, major_mode(%s, %s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator =   coalesce(excluded.operator, log.operator),
dxcc =       coalesce(excluded.dxcc, log.dxcc),
freq =       coalesce(excluded.freq, log.freq),
mode =       coalesce(excluded.mode, log.mode),
submode =    coalesce(excluded.submode, log.submode),
rsttx =      coalesce(excluded.rsttx, log.rsttx),
extx =       coalesce(excluded.extx, log.extx),
rstrx =      coalesce(excluded.rstrx, log.rstrx),
exrx =       coalesce(excluded.exrx, log.exrx),
gridsquare = coalesce(excluded.gridsquare, log.gridsquare),
contest =    coalesce(excluded.contest, log.contest),
upload =     case when %s then excluded.upload else log.upload end,
adif = excluded.adif
"""

def adif_upload(cursor, content, station_callsign, operator, upload_id, contest):
    with transaction.atomic():
        qsos, adif_headers = adif_io.read_from_string(content)
        upload_start, upload_stop = None, None

        for qso in qsos:
            start = adif_io.time_on(qso)
            if start is None:
                continue
            upload_start = min(upload_start, start) if upload_start else start
            upload_stop = max(upload_stop, start) if upload_stop else start

            qso_station = upper(qso.get('STATION_CALLSIGN') or station_callsign \
                    or qso.get('OPERATOR') or operator)
            qso_operator = upper(qso.get('OPERATOR') or operator \
                    or qso.get('STATION_CALLSIGN') or station_callsign)
            if qso_station == qso_operator:
                qso_operator = None

            if not qso_station:
                raise Exception(f"{start} {qso.get('CALL')}: QSO without STATION_CALLSIGN and OPERATOR found in log, set station and/or operator in upload form")

            call = upper(qso.get('CALL'))
            if 'DXCC' in qso and qso.get('DXCC').strip() != '':
                dxcc = qso.get('DXCC')
            else:
                dxcc = country.lookup(call, start)

            freq = qso.get('FREQ')
            mode = upper(qso.get('MODE'))
            submode = upper(qso.get('SUBMODE'))

            cursor.execute(q_insert_qso,
                           [start,
                            qso_station,
                            qso_operator,
                            call,
                            dxcc,
                            lower(qso.get('BAND')),
                            freq, freq,
                            mode, submode, mode, submode,
                            upper(qso.get('RST_SENT')),
                            concat([upper(qso.get('STX')), upper(qso.get('STX_STRING'))]),
                            upper(qso.get('RST_RCVD')),
                            concat([upper(qso.get('SRX')), upper(qso.get('SRX_STRING'))]),
                            upper(qso.get('GRIDSQUARE')),
                            qso.get('CONTEST_ID'),
                            upload_id,
                            json.dumps(qso),
                            contest # contest uploads overwrite old upload ids, other uploads do not
                            ])
        cursor.execute("update upload set qsos = %s, start = date_trunc('minute', %s), stop = date_trunc('minute', %s) where id = %s", [len(qsos), upload_start, upload_stop, upload_id])

    return len(qsos)
