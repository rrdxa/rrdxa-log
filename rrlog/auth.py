from django.db import connection
import base64
from passlib.hash import phpass

def basic_auth(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return False, "Login required"

    token_type, _, credentials = auth_header.partition(' ')
    if token_type.lower() != "basic":
        return False, "Only Basic auth supported"

    username, password = base64.b64decode(credentials).decode("utf-8").split(':')
    username = username.upper()

    with connection.cursor() as cursor:
        cursor.execute("select user_pass from members where call = %s", [username])
        user_password = cursor.fetchone()

        if not user_password:
            print(f"user {username} not found in database")
            return False, "Login failed"

        if not phpass.verify(password, user_password[0]):
            print("wrong password")
            return False, "Login failed"

    return True, username
