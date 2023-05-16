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

# operating time is computed as follows: each QSO is assigned a time range
# around its start time. If the time distance to the QSO before/after is at
# most 15min, then the range starts/ends at half that distance. Otherwise, the
# range border is 1min before/after. (This treats the first/last QSO the same
# as the first/last after/before a break, which could also use different
# numbers.)

q_qso_summary = """
with log_with_op_time as (
    select band, mode, dxcc,
        tstzrange(
        case
            --when lag(start) over (order by start) is null then start - '1 min'::interval
            when lag(start) over (order by start) >= start - '15 min'::interval then
                start - (start - lag(start) over (order by start))/2
            else start - '1 min'::interval
        end,
        case
            --when lead(start) over (order by start) is null then start + '1 min'::interval
            when lead(start) over (order by start) <= start + '15 min'::interval then
                start + (lead(start) over (order by start) - start)/2
            else start + '1 min'::interval
        end, '[]') qso_op_time
    from log where upload = %s
),
data as (
    select
        band::text,
        mode::text,
        count(*) as qsos,
        count(distinct dxcc) as dxccs,
        op_time(range_agg(qso_op_time))
    from log_with_op_time
    group by band, mode
    order by band::band desc, mode
)
select band, mode, qsos, dxccs, op_time::text, round(3600 * qsos / extract(epoch from op_time)) as rate from data
union all
select '', '', sum(qsos), sum(dxccs), sum(op_time)::text, round(3600 * sum(qsos) / extract(epoch from sum(op_time))) from data
"""

def post_summary(cursor, upload_id, send=True):
    cursor.execute(q_upload_data, [upload_id])
    data_arr = namedtuplefetchall(cursor)
    if len(data_arr) == 0:
        return "No data found"
    data = data_arr[0]
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

    if len(summary) > 1: # skip table if it doesn't have band data
        mail += "Band  Mode  QSOs  DXCCs  Time   Rate\n"
        for b in summary:
            mail += f"{b.band:4}  {b.mode:4}  {b.qsos:4}  {b.dxccs:5}  {b.op_time[:-3]:5}  {b.rate:4}\n"
        mail += "\n"
    else:
        mail += "No QSO data found\n\n"

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
