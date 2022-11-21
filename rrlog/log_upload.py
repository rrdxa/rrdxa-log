from rrlog import adif_io

def log_upload(connection, request, person):
    data = request.POST
    adif = request.FILES['logfile'].read().decode(encoding='UTF-8', errors='backslashreplace')

    call = data.get('call') or None
    operator = data.get('operator') or None
    contest = data.get('contest') or None

    with connection.cursor() as cursor:
        cursor.execute("insert into person (person, last_seen) values (%s, now()) on conflict (person) do update set last_seen = now()", [person])
        if call:
            cursor.execute("insert into call (call) values (%s) on conflict (call) do nothing", [call])
        if operator:
            cursor.execute("insert into call (call) values (%s) on conflict (call) do nothing", [operator])

        cursor.execute("insert into upload (person, call, operator, contest, adif) values (%s, %s, %s, %s, %s) returning id",
                       [person, call, operator, contest, adif])
        upload_id = cursor.fetchone()
        connection.commit()

        try:
            qsos, adif_headers = adif_io.read_from_string(adif)
            for qso in qsos:
                cursor.execute("insert into log (start, station_callsign, operator, call, cty, band, freq, mode, rsttx, rstrx, contest, upload, adif) " +
                               "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) " +
                               "on conflict (station_callsign, call, start) do update set " +
                               "operator = excluded.operator, cty = excluded.cty, band = excluded.band, freq = excluded.freq, mode = excluded.mode, rsttx = excluded.rsttx, rstrx = excluded.rstrx, contest = excluded.contest, upload = excluded.upload",
                               [adif_io.time_on(qso),
                                qso.get('STATION_CALLSIGN') or call or qso.get('OPERATOR') or operator,
                                qso.get('OPERATOR') or operator,
                                qso.get('CALL'),
                                qso.get('CTY'),
                                qso.get('BAND'),
                                qso.get('FREQ'),
                                qso.get('MODE'),
                                qso.get('RSTTX'),
                                qso.get('RSTRX'),
                                qso.get('CONTEST'),
                                upload_id,
                                qso])

        except Exception as e:
            cursor.execute("update upload set error = %s where id = %s", [str(e), upload_id])
            connection.commit()
            return e

    return f"Upload stored as id {upload_id}"

