from django.db import models

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
