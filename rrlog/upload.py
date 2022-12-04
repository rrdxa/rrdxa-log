from django.db import transaction
from rrlog import adif_io, country

def lower(text):
    if text == None:
        return None
    return text.lower()

def upper(text):
    if text == None:
        return None
    return text.upper()

q_insert_qso = """insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, rsttx, rstrx, gridsquare, contest, upload)
values (date_trunc('minute', %s), %s, nullif(%s, %s), %s, %s, coalesce(%s::band, %s::numeric::band), %s, major_mode(%s), %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator = excluded.operator,
dxcc = excluded.dxcc,
band = excluded.band,
freq = excluded.freq,
major_mode = excluded.major_mode,
mode = excluded.mode,
rsttx = excluded.rsttx,
rstrx = excluded.rstrx,
gridsquare = excluded.gridsquare,
contest = excluded.contest,
upload = excluded.upload"""

def log_upload(connection, request, username):
    data = request.POST
    filename = request.FILES['logfile'].name
    adif = request.FILES['logfile'].read().decode(encoding='UTF-8', errors='backslashreplace')

    station_callsign = upper(data.get('station_callsign'))
    operator = upper(data.get('operator'))
    contest = data.get('contest') or None

    with connection.cursor() as cursor:
        cursor.execute("insert into upload (uploader, filename, station_callsign, operator, contest, adif) values (%s, %s, %s, %s, %s, %s) returning id",
                       [username, filename, station_callsign, operator, contest, adif])
        upload_id = cursor.fetchone()

        try:
            with transaction.atomic():
                qsos, adif_headers = adif_io.read_from_string(adif)
                for qso in qsos:
                    start = adif_io.time_on(qso)
                    qso_station = qso.get('STATION_CALLSIGN') or station_callsign
                    qso_operator = qso.get('OPERATOR') or operator

                    if not station_callsign and not operator:
                        raise Exception(f"{start} {qso.get('CALL')}: QSO without STATION_CALLSIGN and OPERATOR found in log, set station and/or operator in upload form")

                    call = upper(qso.get('CALL'))
                    if 'DXCC' in qso:
                        dxcc = qso.get('DXCC')
                    else:
                        dxcc = country.lookup(call, start)

                    tx_rpts = [upper(qso.get('RST_SENT')), upper(qso.get('STX')), upper(qso.get('STX_STRING'))]
                    rsttx = ' '.join(filter(None, tx_rpts)) or None
                    rx_rpts = [upper(qso.get('RST_RCVD')), upper(qso.get('SRX')), upper(qso.get('SRX_STRING'))]
                    rstrx = ' '.join(filter(None, rx_rpts)) or None

                    freq = qso.get('FREQ')
                    mode = upper(qso.get('MODE')),

                    gridsquare = qso['GRIDSQUARE'][:4].upper() \
                        if 'GRIDSQUARE' in qso else None

                    cursor.execute(q_insert_qso,
                                   [start,
                                    qso_station or qso_operator,
                                    qso_operator or qso_station, qso_operator or qso_station,
                                    call,
                                    dxcc,
                                    lower(qso.get('BAND')),
                                    freq, freq,
                                    mode, mode,
                                    rsttx,
                                    rstrx,
                                    gridsquare,
                                    qso.get('CONTEST'),
                                    upload_id,
                                    ])
                cursor.execute("update upload set qsos = %s where id = %s", [len(qsos), upload_id])

        except Exception as e:
            cursor.execute("update upload set error = %s where id = %s", [str(e), upload_id])
            return e

    return f"{len(qsos)} QSOs recorded in database"

