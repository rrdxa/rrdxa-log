from passlib.hash import bcrypt, phpass

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from .models import Member

class WordpressAuthBackend(BaseBackend):
    def get_user(self, user_id):
        print("hey get_user")
        try:
            user = User.objects.get(pk=user_id)
            print("get_user", user)
            return user
        except User.DoesNotExist:
            print("get_user DoesNotExist")
            return None

    def authenticate(self, request, username=None, password=None):
        print("hey authenticate")
        try:
            user = Member.objects.get(call=username)
        except Member.DoesNotExist:
            print("no member found")
            return None

        # Wordpress 6.8 switched from phpass ($P$) to custom sha256+bcrypt ($wp$2y$).
        # Since that isn't supported by passlib yet, we deploy
        # https://wordpress.org/plugins/password-hash/ on the Wordpress side so
        # it's writing standard bcrypt ($2y$) now.
        if user.user_pass[:2] == '$2':
            hash_method = bcrypt
        elif user.user_pass[:3] == '$P$':
            hash_method = phpass
        else:
            raise Exception(f"unknown password hash scheme for user {user}")

        if not hash_method.verify(password, user.user_pass):
            return None

        DjangoUser = get_user_model()
        django_user, created = DjangoUser.objects.get_or_create(username=user.call)
        if created:
            django_user.is_staff = user.admin
            django_user.save()
        print('user:', django_user)
        return django_user
