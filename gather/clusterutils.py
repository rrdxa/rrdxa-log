import re
import time
import datetime

def str_to_timestamp(s):
    now = time.strftime('%H%M', time.gmtime())
    if s > now:
        return f"yesterday {s}"
    else:
        return f"today {s}"

def int_to_timestamp(i):
    return datetime.datetime.fromtimestamp(i, datetime.timezone.utc)

def last_spot(cur, source, cluster):
    cur.execute("select max((value->>'spot_time')::timestamptz) from bandmap, jsonb_array_elements(data['spots']) where source = %s and value->>'cluster' = %s", [source, cluster])
    return cur.fetchone()[0] or int_to_timestamp(0)

dx_re = re.compile(r'DX de ([\w\d/#-]+):? *([\d.]+) +([^ ]+) +(\S(?:.*\S)?)? +(\d\d\d\d)Z *(.*[^\a ])?')

def parse_spot(line, source=None, cluster=None):
    m = re.match(dx_re, line)

    if not m:
        return None

    return {'source': source,
            'cluster': cluster,
            'spotter': m.group(1),
            'qrg': m.group(2),
            'dx': m.group(3),
            'info': m.group(4),
            'spot_time': str_to_timestamp(m.group(5)),
            'spotter_loc': m.group(6),
            }

mode_re = r'CW|SSB|LSB|USB|FM|RTTY|PSK\d*|FT\d+|MSK\d*'
loc_re = r'\b[A-R][A-R][0-9][0-9](?:[A-X][A-X](?:[0-9][0-9](?:[A-X][A-X])?)?)?'

def parse_cluster_info(info, spot):
    if info is None:
        return
    if m := re.match(f'({mode_re})\\b', info, re.I):
        spot['mode'] = m.group(1).upper()

    if m := re.search(f'\\b({loc_re})\\s*(?:<\\S*>|->)\\s*({loc_re})?\\b(?:\\s+({mode_re})\\b)?', info, re.I):
        if m.group(1):
            spot['spotter_loc'] = m.group(1).upper()
        if m.group(2):
            spot['dx_loc'] = m.group(2).upper()
        if m.group(3):
            spot['mode'] = m.group(3).upper()

    if m := re.search(r'(?:^|\s)([+-]?\d+)\s*dB\b', info, re.I):
        spot['db'] = int(m.group(1))
    elif m := re.search(r'(?:^|\s)([+-]\d+\b)', info):
        spot['db'] = int(m.group(1))

    if m := re.search(r'\b(\d+)\s*(wpm|bps)\b', info, re.I):
        spot['wpm'] = int(m.group(1))

def insert_spot(cur, spot):
    cur.execute("insert into rrdxa.incoming (" +
                ', '.join(spot.keys()) +
                ") values (" +
                ', '.join('%s' for x in spot.values()) +
                ")",
                [x for x in spot.values()])

def format_spot(m):
    spot = m['spots'][0] if 'spots' in m and len(m['spots'][0]) > 0 else {}
    spotter = spot.get('spotter') or '??'
    qrg = m.get('qrg') or '??'
    dx = m.get('dx') or '??'

    if 'info' in spot and spot['info'] is not None:
        info = f"{spot['info']} " # space at end so we can append more items
    elif 'mode' in m and m['mode'] is not None:
        info = f"{m['mode']} "
    else:
        info = ""

    if 'db' in spot and spot['db'] is not None and 'dB' not in info:
        info += f"{spot['db']} dB "
    if 'wpm' in m and m['wpm'] is not None and 'WPM' not in info:
        info += f"{m['wpm']} WPM "
    if 'cluster' in spot:
        info += f"[{spot['cluster']}] "
    else:
        info += f"[{m['source']}] "

    ts = m['spot_time'][11:13] + m['spot_time'][14:16]
    spotter_loc = spot.get('spotter_loc') or ''

    # try to match the original cluster column layout as close as possible, but without truncating dx and qrg
    # DX de IK5WOB:     3520.0  IQ5PJ        Coltano Marconi Award          1656Z JN53
    return f"DX de {spotter[:10]+':':11}{qrg:7}  {dx:12} {info[:30]:30} {ts}Z {spotter_loc[:6]}"
