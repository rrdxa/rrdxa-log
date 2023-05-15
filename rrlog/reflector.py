#from django.db import transaction
#import re
#from rrlog import cabrillo, country
from rrlog.utils import namedtuplefetchall
from email.message import EmailMessage
import smtplib

q_upload_data = """select uploader,
contest,
station_callsign,
operators,
club,
category_operator,
category_assisted,
category_band,
category_mode,
category_overlay,
category_power,
category_station,
category_time,
category_transmitter,
location,
grid_locator,
soapbox,
claimed_score
from upload where id = %s
"""

# operating time is computed as follows: each QSO is assigned the aligned
# 10-minute interval in which it took place, and then the number of distinct
# intervals is counted. Since multiple bands can be used within an interval,
# the total op time will usually be less than the sum of the band times.

q_qso_summary = """with data as (
    select
        band::text,
        mode::text,
        count(*) as qsos,
        count(distinct dxcc) as dxccs,
        range_agg(qso_time_interval(start, '10 min'::interval)) as time_intervals
    from log
    where upload = %s
    group by band, mode
    order by band desc, mode
)
select band, mode, qsos, dxccs, op_time(time_intervals)::text from data
union all
select '', '', sum(qsos), sum(dxccs), op_time(range_agg(time_intervals))::text from data
"""

def post_summary(cursor, upload_id, send=True):
    cursor.execute(q_upload_data, [upload_id])
    data = namedtuplefetchall(cursor)[0]
    cursor.execute(q_qso_summary, [upload_id])
    summary = namedtuplefetchall(cursor)

    # build subject
    subject = f"{data.station_callsign} {data.contest} {data.category_operator}"
    if data.category_band and data.category_band != 'ALL': subject += f" {data.category_band}"
    if data.category_mode and data.category_mode != 'ALL': subject += f" {data.category_mode}"
    if data.category_assisted: subject += f" {data.category_power} {data.category_assisted}"

    # build content
    mail = f"{subject}\n\n"

    mail +=                               f"Callsign:    {data.station_callsign}\n"
    if data.operators and data.operators != data.station_callsign:
                                  mail += f"Operators:   {data.operators}\n"
    if data.club:                 mail += f"Club:        {data.club}\n"
    if data.location:             mail += f"Location:    {data.location}\n"
    if data.grid_locator:         mail += f"Locator:     {data.grid_locator}\n"
    mail += "\n"

    if data.contest:              mail += f"Contest:     {data.contest}\n"
    if data.category_operator:    mail += f"Category:    {data.category_operator}\n"
    if data.category_band:        mail += f"Band:        {data.category_band}\n"
    if data.category_mode:        mail += f"Mode:        {data.category_mode}\n"
    if data.category_power:       mail += f"Power:       {data.category_power}\n"
    if data.category_overlay:     mail += f"Overlay:     {data.category_overlay}\n"
    if data.category_time:        mail += f"Time:        {data.category_time}\n"
    if data.category_transmitter and data.category_transmitter != 'ONE':
                                  mail += f"Transmitter: {data.category_transmitter}\n"
    if data.category_assisted:    mail += f"Assisted:    {data.category_assisted}\n"
    mail += "\n"

    mail += "Band  Mode  QSOs  DXCCs  Time\n"
    for b in summary:
        mail += f"{b.band:4}  {b.mode:4}  {b.qsos:4}  {b.dxccs:5}  {b.op_time[:-3]}\n"
    mail += "\n"

    if data.claimed_score: mail += f"Claimed score: {data.claimed_score}\n\n"

    if data.soapbox:
        mail += f"Soapbox:\n\n{data.soapbox}\n\n"

    # send it
    if send:
        msg = EmailMessage()
        msg['Message-Id'] = f"<cabrillo-upload-{upload_id}@rrdxa.org>"
        msg['From'] = f"{data.uploader} via rrdxa.org <logbook@rrdxa.org>"
        msg['To'] = f"{data.contest} score submission <rrdxa@mailman.qth.net>"
        msg['Subject'] = subject
        msg['X-Callsign'] = data.station_callsign
        msg['X-Contest'] = data.contest
        msg.set_content(mail)
        with smtplib.SMTP('localhost') as smtp:
            smtp.send_message(msg)

    return mail
