from django.http import HttpResponse
from django.db import connection
from rrlog import country
import dateutil.parser
import json

def lookup(request, call):
    if 'date' in request.GET:
        ts = dateutil.parser.parse(request.GET.get('date'))
    else:
        ts = None

    info = country.info(call, ts)

    if info is None:
        js = '{}'
        status = 404
    else:
        js = json.dumps(info)
        status = 200
    response = HttpResponse(js, status=status, content_type='application/json')
    return response

def spots(request, channel):
    with connection.cursor() as cursor:
        cursor.execute("select jsonb_agg(data order by spot_time) from (select spot_time, jsonb_set_lax(data, '{spots}', jsonb_build_array(data['spots'][0])) as data from bandmap join rule on data @@ jsfilter where channel = %s order by spot_time desc limit 500)", [channel])
        json = cursor.fetchone()[0] or '[]'
    response = HttpResponse(json, content_type='application/json')
    return response
