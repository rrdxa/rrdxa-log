from django.contrib import admin
from .models import Member, Vereinsmitglied, Zahlung

class MemberAdmin(admin.ModelAdmin):
    list_display = ('call', 'display_name', 'member_no')

admin.site.register(Member, MemberAdmin)

class VereinsmitgliedAdmin(admin.ModelAdmin):
    list_display = ('call', 'display_name', 'member_no')

    search_fields = ('call', 'display_name')

admin.site.register(Vereinsmitglied, VereinsmitgliedAdmin)

admin.site.register(Zahlung)
