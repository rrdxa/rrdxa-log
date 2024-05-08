from django.db import connection
from django.shortcuts import render
import base64
from passlib.hash import phpass
import functools

def basic_auth(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return False, "Login required"

    token_type, _, credentials = auth_header.partition(' ')
    if token_type.lower() != "basic":
        return False, "Only Basic auth supported"

    username, _, password = base64.b64decode(credentials).decode("utf-8").partition(':')

    with connection.cursor() as cursor:
        cursor.execute("select call, user_pass from members where call = %s or user_email = %s", [username.upper(), username.lower()])
        userdata = cursor.fetchone()

    if not userdata:
        print(f"user {username} not found in database")
        return False, "Login failed"

    username, user_password = userdata

    if not phpass.verify(password, user_password):
        print("wrong password for user {username}")
        return False, "Login failed"

    return True, username

def auth_required(func):
    """Make sure the user is logged in before delivering this page"""

    @functools.wraps(func)
    def wrapper_auth_required(request, *args, **kwargs):
        status, message = basic_auth(request)
        if not status:
            response = render(request, 'rrlog/generic.html', { 'message': message }, status=401)
            response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
            return response
        request.username = message
        return func(request, *args, **kwargs)

    return wrapper_auth_required
