from django.contrib import admin

# Register your models here.
from .models import User, VerificationCode, Report , PacketDetail , PacketEvent
# PrivacyScan, PrivacyIssue,
admin.site.register(User)
admin.site.register(VerificationCode)
# admin.site.register(PrivacyScan)
# admin.site.register(PrivacyIssue)
admin.site.register(Report)
admin.site.register(PacketDetail)
admin.site.register(PacketEvent)