from rrlog.utils import upper
from rrlog.adif_upload import adif_upload
from rrlog.cabrillo_upload import cabrillo_upload

def log_upload(connection, request, username):
    data = request.POST
    filename = request.FILES['logfile'].name
    content = request.FILES['logfile'].read().decode(encoding='UTF-8', errors='backslashreplace')
    upper_content = upper(content)

    if '<EOR>' in upper_content:
        logtype = 'adif'
        station_callsign = upper(data.get('station_callsign')) or None
        operator = upper(data.get('operator')) or None
        contest = data.get('contest') or False
    elif 'START-OF-LOG' in upper_content:
        logtype = 'cabrillo'
        contest = True
    else:
        return None, False, "Supported log types are ADIF and Cabrillo, this seems like neither of them"

    with connection.cursor() as cursor:
        cursor.execute("insert into upload (uploader, filename, adif) values (%s, %s, %s) returning id",
                       [username, filename, content])
        (upload_id,) = cursor.fetchone()

        try:
            if logtype == 'adif':
                num_qsos = adif_upload(cursor, content, station_callsign, operator, contest, upload_id)
            elif logtype == 'cabrillo':
                num_qsos = cabrillo_upload(cursor, content, upload_id)

        except Exception as e:
            cursor.execute("update upload set error = %s where id = %s", [str(e), upload_id])
            raise
            return None, False, e

    return upload_id, contest, f"{num_qsos} QSOs recorded in database"
