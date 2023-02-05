# thanks https://simpleisbetterthancomplex.com/snippet/2016/08/22/dealing-with-querystring-parameters.html

from django import template

register = template.Library()

@register.simple_tag
def relative_url(key, value, querystring=None):
    url_params = []
    if querystring:
        parameters = querystring.split('&')
        url_params += filter(lambda p: p.split('=')[0] != key, parameters)
    if value != None:
        url_params.append(f"{key}={value}")
    return '?' + '&'.join(url_params)
