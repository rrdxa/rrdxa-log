from django.http import HttpResponse
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
