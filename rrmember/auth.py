from passlib.hash import bcrypt, phpass

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from .models import Member

class WordpressAuthBackend(BaseBackend):
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            return None

    def authenticate(self, request, username=None, password=None):
        username = username.upper()

        try:
            wpuser = Member.objects.get(call=username)
        except Member.DoesNotExist:
            print(f"Login failed for {username}, user does not exist")
            return None

        # Wordpress 6.8 switched from phpass ($P$) to custom sha256+bcrypt ($wp$2y$).
        # Since that isn't supported by passlib yet, we deploy
        # https://wordpress.org/plugins/password-hash/ on the Wordpress side so
        # it's writing standard bcrypt ($2y$) now.
        if wpuser.user_pass[:2] == '$2':
            hash_method = bcrypt
        elif wpuser.user_pass[:3] == '$P$':
            hash_method = phpass
        else:
            raise Exception(f"unknown password hash scheme for user {wpuser}")

        if not hash_method.verify(password, wpuser.user_pass):
            print(f"Login failed for {username}, wrong password")
            return None

        DjangoUser = get_user_model()
        django_user, _ = DjangoUser.objects.get_or_create(
                username=wpuser.call,
                defaults={
                    'first_name': wpuser.first_name,
                    'last_name': wpuser.last_name,
                    'email': wpuser.user_email,
                    'is_staff': wpuser.admin,
                })
        return django_user
