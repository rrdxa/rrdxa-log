from rrlog.utils import upper
from rrlog.adif_upload import adif_upload
from rrlog.cabrillo_upload import cabrillo_upload
from rrlog.reflector import post_summary

def log_upload(connection, request, username):
    data = request.POST
    filename = request.FILES['logfile'].name
    content = request.FILES['logfile'].read().decode(encoding='UTF-8', errors='backslashreplace')

    station_callsign = upper(data.get('station_callsign')) or None
    operator = upper(data.get('operator')) or None
    contest = data.get('contest') or None

    upper_content = upper(content)
    if '<EOR>' in upper_content:
        logtype = 'adif'
    elif 'START-OF-LOG' in upper_content:
        logtype = 'cabrillo'
    else:
        return "Supported log types are ADIF and Cabrillo, this seems like neither of them"

    with connection.cursor() as cursor:
        cursor.execute("insert into upload (uploader, filename, station_callsign, operator, contest, adif) values (%s, %s, %s, %s, %s, %s) returning id",
                       [username, filename, station_callsign, operator, contest, content])
        (upload_id,) = cursor.fetchone()

        try:
            if logtype == 'adif':
                num_qsos = adif_upload(cursor, content, station_callsign, operator, contest, upload_id)
            elif logtype == 'cabrillo':
                num_qsos = cabrillo_upload(cursor, content, station_callsign, operator, contest, upload_id)

                # prepend soapbox from form to soapbox in cabrillo file
                soapbox = data.get('soapbox') or None
                if soapbox:
                    cursor.execute("update upload set soapbox = concat_ws(E'\n\n', %s, soapbox) where id = %s", [soapbox, upload_id])

                # post summary to reflector
                reflector = data.get('reflector') or None
                if reflector:
                    post_summary(cursor, upload_id)

        except Exception as e:
            cursor.execute("update upload set error = %s where id = %s", [str(e), upload_id])
            raise
            return e

    return f"{num_qsos} QSOs recorded in database"
