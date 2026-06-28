from django import views
from django.contrib import admin
from django.urls import path

from accounts.views import (
    RegisterUser,
    VerifyCode,
    Reset_Password,
    LoginView,
    LogoutView,
    UserMeView,
    UserPasswordView,
    # ReportsListView,
    
    # PlatformReportView,   # <-- NEW view name (neeche code dunga)
    PacketView,
    PacketAnalysisView,
    InstantReportWithAIView,
    # attack_sim,
    # spam_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path("api/register/", RegisterUser.as_view(), name="register_api"),
    path("api/signup/", RegisterUser.as_view(), name="signup_api"),
    path("api/verify/", VerifyCode.as_view(), name="verify"),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/reset_password/", Reset_Password.as_view(), name="reset_password"),
    path("api/logout/", LogoutView.as_view(), name="logout"),

    # User
    path("api/user/me/", UserMeView.as_view(), name="user_me"),
    path("api/user/password/", UserPasswordView.as_view(), name="user_password"),

    # # Reports
    # path("api/reports/", ReportsListView.as_view(), name="reports_list"),
    # path("api/reports/<int:report_id>/", ReportDetailView.as_view(), name="report_detail"),

    # ✅ Platform reports (NO conflict)
    path("api/reports/instant-ai/", InstantReportWithAIView.as_view(), name="instant_report_ai"),

    # Packets
    path("api/packets/", PacketView.as_view(), name="packets"),
    path("api/packets-analyze/", PacketAnalysisView.as_view(), name="packet_analysis"),
    
    #spam requests
    # path("api/spam/", spam_view.as_view(), name="spam_requests"),
    # path("api/attack-sim/", attack_sim.as_view(), name="attack_sim"),
]
