from django.contrib import admin
from .models import Member, Vereinsmitglied, Zahlung

# members (the list of accounts synced from Wordpress)


class MemberAdmin(admin.ModelAdmin):
    list_display = ("call", "display_name", "member_no")
    search_fields = ("call", "display_name", "member_no")
    list_per_page = 500


admin.site.register(Member, MemberAdmin)

# verein (the list of accounts kept locally, synced from members)


@admin.action(description="Jahresbeitragszahlung aufnehmen")
def jahresbeitrag(modeladmin, request, queryset):
    for mitglied in queryset.all():
        mitglied.zahle_jahresbeitrag()


class VereinsmitgliedAdmin(admin.ModelAdmin):
    list_display = ("call", "display_name", "member_no")
    search_fields = ("call", "display_name", "member_no")
    list_per_page = 500
    actions = [jahresbeitrag]


admin.site.register(Vereinsmitglied, VereinsmitgliedAdmin)

# verein_zahlung (payment received from members)

admin.site.register(Zahlung)
