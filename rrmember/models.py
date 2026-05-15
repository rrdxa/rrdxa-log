from django.db import models
from django.contrib.auth.models import User

class Member(models.Model):
    call = models.CharField(primary_key=True)
    callsigns = models.CharField() # text[]
    member_no = models.IntegerField()
    display_name = models.CharField()
    first_name = models.CharField()
    last_name = models.CharField()
    nickname = models.CharField()
    user_email = models.CharField()
    user_pass = models.CharField()
    wpid = models.IntegerField()
    user_roles = models.CharField() # text[]
    public = models.BooleanField()
    admin = models.BooleanField()

    def __str__(self):
        return f"{self.display_name}, {self.call}"

    class Meta:
        db_table = "members"
        managed = False
        ordering = ('call',)

class Vereinsmitglied(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL)
    member_no = models.IntegerField(primary_key=True)
    call = models.CharField(blank=False, null=False)
    display_name = models.CharField(blank=False, null=False)
    account_created = models.DateField(auto_now_add=True)
    vereinsbeitritt = models.DateField(blank=True, null=True)
    bezahlt_bis = models.DateField(blank=True, null=True)
    vereinsaustritt = models.DateField(blank=True, null=True)
    silent_key = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.display_name}, {self.call} (#{self.member_no})"

    class Meta:
        db_table = "verein"
        ordering = ('call',)

class Zahlung(models.Model):
    mitglied = models.ForeignKey(Vereinsmitglied, on_delete=models.PROTECT)
    datum = models.DateField(blank=False, null=False)
    betrag = models.DecimalField(blank=False, null=False, max_digits=10, decimal_places=2)
    betreff = models.CharField(max_length=1000)
