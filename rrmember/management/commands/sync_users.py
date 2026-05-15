from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.contrib.auth.models import User
from rrmember.models import Member, Vereinsmitglied

class Command(BaseCommand):
    help = "Import users from wordpress and sync with our database"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("refresh materialized view rrdxa.members;")
            cursor.execute("refresh materialized view rrdxa.rrcalls;")

        for member in Member.objects.all():
            user, created = User.objects.get_or_create(username=member.call.upper(), defaults={
                "first_name": member.first_name,
                "last_name": member.last_name,
                "email": member.user_email,
            })
            #user.email = member.user_email
            #user.save()
            if created:
                print("Neuer Wordpress-User:", user)

            if member.member_no:
                mitglied, created = Vereinsmitglied.objects.get_or_create(member_no = member.member_no, defaults={
                    "call": member.call.upper(),
                    "display_name": member.display_name,
                    "user": user,
                })
                if created:
                    print("Neues Vereinsmitglied:", mitglied)

