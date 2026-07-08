from django.db import models
from django.contrib.auth.models import User
from datetime import date
from rrdxa import settings

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
        return f"{self.call}, {self.display_name} (#{self.member_no})"

    class Meta:
        db_table = "verein"
        ordering = ('call',)

    def zahle_jahresbeitrag(self):
        Zahlung.objects.create(
                mitglied=self,
                datum=date.today(),
                betrag=settings.JAHRESBEITRAG,
                betreff="Jahresbeitrag",
                )
        if self.vereinsbeitritt is None:
            self.vereinsbeitritt = date.today()
        if self.bezahlt_bis is None:
            day = date.today()
        else:
            day = self.bezahlt_bis
        self.bezahlt_bis = date(day.year + 1, day.month, day.day)
        self.save()

class Zahlung(models.Model):
    mitglied = models.ForeignKey(Vereinsmitglied, on_delete=models.PROTECT)
    datum = models.DateField(blank=False, null=False)
    betrag = models.DecimalField(blank=False, null=False, max_digits=10, decimal_places=2)
    betreff = models.CharField(max_length=1000)

    def __str__(self):
        return f"{self.datum} {self.mitglied}: {self.betrag} € ({self.betreff})"

    class Meta:
        db_table = "verein_zahlung"
        ordering = ('datum', 'mitglied')
