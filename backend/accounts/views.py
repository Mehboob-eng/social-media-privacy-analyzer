from datetime import timedelta
# from django.http import JsonResponse
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from requests import request
from rest_framework import generics
import time
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count
from rest_framework_simplejwt.tokens import RefreshToken
from .ai_report import gen_report
from .helper_method import generate_otp_code
from django.db.models import Sum
from .models import (
User, 
VerificationCode , 
PacketDetail,
PacketEvent,
# Report
)
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    
    UserSerializer,
    UserSerializer1,
    packetDetailSerializer,
    # ReportSerializer,
)


class RegisterUser(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password")

        if not email or not username or not password:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

        otp_code = generate_otp_code()

        # keep at most one active signup code per (email, purpose)
        with transaction.atomic():
            vc, _ = VerificationCode.objects.update_or_create(
                email=email,
                purpose=VerificationCode.PURPOSE_SIGNUP,
                defaults={
                    "user": None,
                    "code_hash": make_password(otp_code),
                    "expires_at": timezone.now() + timedelta(minutes=5),
                    "attempts": 0,
                    "consumed_at": None,
                    "meta_json": {
                        "username": username,
                        "password": make_password(password),  # keeping your current approach
                    },
                },
            )

        # TODO: send otp_code by email
        print("SIGNUP OTP:", otp_code)  # dev only

        return Response({"id": vc.id, "OTP_SENT": True}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Login Flow:
        - username OR email + password
        - If 2FA enabled → send OTP (replace existing active OTP safely)
        - Else → return JWT tokens
        """
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = ser.validated_data["user"]

        if user.two_factor_enabled:
            otp_code = generate_otp_code()

            with transaction.atomic():
                vc, _ = VerificationCode.objects.update_or_create(
                    email=user.email,
                    purpose=VerificationCode.PURPOSE_LOGIN_2FA,
                    defaults={
                        "user": user,
                        "code_hash": make_password(otp_code),
                        "expires_at": timezone.now() + timedelta(minutes=5),
                        "attempts": 0,
                        "consumed_at": None,
                        "meta_json": {"username": user.username},
                    },
                )

            # TODO: send otp_code by email
            print("LOGIN OTP:", otp_code)  # dev only

            return Response(
                {"id": vc.id, "OTP_SENT": True, "two_factor": True},
                status=status.HTTP_201_CREATED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {"token": {"refresh": str(refresh), "access": str(refresh.access_token)}, "two_factor": False},
            status=status.HTTP_200_OK,
        )


class VerifyCode(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Verify OTP for:
        - signup_email (creates user)
        - login_2fa (returns tokens)
        Body: { "id": "<verification_id>", "otp": "<code>" }
        """
        otp = request.data.get("otp")
        vc_id = request.data.get("id")

        if not otp or not vc_id:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        vc = VerificationCode.objects.filter(id=vc_id).first()
        if not vc:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        if vc.expires_at and vc.expires_at < timezone.now():
            return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

        if vc.consumed_at:
            return Response({"error": "OTP has already been consumed"}, status=status.HTTP_400_BAD_REQUEST)

        if vc.attempts >= 2:
            return Response({"error": "Maximum attempts reached"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(otp, vc.code_hash):
            vc.bump_attempts(max_times=2)
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is valid → act by purpose
        if vc.purpose == VerificationCode.PURPOSE_SIGNUP:
            meta = vc.meta_json or {}

            user_payload = {
                "email": vc.email,
                "username": meta.get("username"),
                "password": meta.get("password"),  # already hashed (your current pattern)
                "email_verified": True,
                "two_factor_enabled": False,
            }

            with transaction.atomic():
                user_ser = UserSerializer(data=user_payload)
                user_ser.is_valid(raise_exception=True)
                user = user_ser.save()

                vc.consume()

            return Response({"message": "User created successfully", "user_id": user.id}, status=status.HTTP_200_OK)

        if vc.purpose == VerificationCode.PURPOSE_LOGIN_2FA:
            user = vc.user
            if not user:
                return Response({"error": "Invalid verification context"}, status=status.HTTP_400_BAD_REQUEST)

            vc.consume()

            refresh = RefreshToken.for_user(user)
            return Response(
                {"token": {"refresh": str(refresh), "access": str(refresh.access_token)}},
                status=status.HTTP_200_OK,
            )

        return Response({"error": "Unsupported purpose"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Reset password confirmation
        Body: { "id": "<verification_id>", "otp": "<code>", "password": "<new_password>" }
        """
        otp = request.data.get("otp")
        vc_id = request.data.get("id")
        new_password = request.data.get("password")

        if not otp or not vc_id or not new_password:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        vc = VerificationCode.objects.filter(id=vc_id).first()
        if not vc:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        if vc.expires_at and vc.expires_at < timezone.now():
            return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

        if vc.consumed_at:
            return Response({"error": "OTP has already been consumed"}, status=status.HTTP_400_BAD_REQUEST)

        if vc.attempts >= 2:
            return Response({"error": "Maximum attempts reached"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(otp, vc.code_hash):
            vc.bump_attempts(max_times=2)
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # Only allow reset_password purpose for PUT
        if vc.purpose != VerificationCode.PURPOSE_RESET:
            return Response({"error": "Invalid verification purpose"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=vc.email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        vc.consume()
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)


class Reset_Password(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Start password reset
        Body: { "username": "<user_username>" }  (you can extend to email later)
        """
        username = (request.data.get("username") or "").strip()
        if not username:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(username=username).first()
        if not user:
            return Response({"error": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        otp_code = generate_otp_code()

        with transaction.atomic():
            vc, _ = VerificationCode.objects.update_or_create(
                email=user.email,
                purpose=VerificationCode.PURPOSE_RESET,
                defaults={
                    "user": user,
                    "code_hash": make_password(otp_code),
                    "expires_at": timezone.now() + timedelta(minutes=5),
                    "attempts": 0,
                    "consumed_at": None,
                    "meta_json": {"username": user.username},
                },
            )

        # TODO: send otp_code by email
        print("RESET OTP:", otp_code)  # dev only

        # Mask email (light UX)
        try:
            at_idx = user.email.index("@")
            masked = f"{user.email[:max(0, at_idx-2)]}**{user.email[at_idx:]}"
        except Exception:
            masked = user.email

        return Response({"id": vc.id, "OTP_SENT": True, "email": masked}, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Logout:
        Body: { "refresh": "<refresh_token>" }
        """
        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        token = RefreshToken(ser.validated_data["refresh"])
        token.blacklist()
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)

class InstantReportWithAIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Generate instant spam vs non-spam report
        using aggregated PacketDetail data
        """

        # Optional filter by platform (facebook, twitter, etc.)
        platform = request.query_params.get("platform")

        # Fetch packet summary data
        qs = PacketDetail.objects.filter(user=request.user)

        if platform:
            qs = qs.filter(hostname=platform)

        # Aggregate totals
        spam_count = qs.aggregate(
            total_spam=Sum("is_spam")
        )["total_spam"] or 0

        non_spam_count = qs.aggregate(
            total_non_spam=Sum("not_spam")
        )["total_non_spam"] or 0

        total = spam_count + non_spam_count
        accuracy = (non_spam_count / total) * 100 if total else 0

        # Prepare data for graph (bar chart)
        graph = {
            "type": "bar",
            "labels": ["Spam", "Non-Spam"],
            "values": [spam_count, non_spam_count]
        }

        # AI-generated report text
        platform_name = platform or "all platforms"
        ai_text = gen_report(
            platform_name,
            spam_count,
            non_spam_count
        )

        # Final response
        return Response({
            "platform": platform_name,
            "summary": {
                "spam": spam_count,
                "non_spam": non_spam_count,
                "total": total,
                "accuracy": round(accuracy, 2)
            },
            "graph": graph,
            "ai_report": ai_text
        }, status=status.HTTP_200_OK)

        

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = UserSerializer1(request.user)
        return Response(ser.data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user

        # Optional: change password inside profile update (kept from your logic)
        if request.data.get("new_password"):
            current_password = request.data.get("current_password")
            if not current_password or not user.check_password(current_password):
                return Response({"error": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(request.data.get("new_password"))
            user.save(update_fields=["password"])
            return Response({"success": True}, status=status.HTTP_200_OK)

        ser = UserSerializer1(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_200_OK)

    def delete(self, request):
        request.user.delete()
        return Response({"success": True}, status=status.HTTP_200_OK)


class UserPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"detail": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        u = request.user
        if not u.check_password(current_password):
            return Response({"detail": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"detail": "New password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

        u.set_password(new_password)
        u.save(update_fields=["password"])
        return Response({"message": "Password changed"}, status=status.HTTP_200_OK)




class PacketView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        
        # {'hostname': 'gateway.facebook.com', 'src_ip': '192.168.1.6',
        #  'src_port': 51801, 'dst_ip': '57.144.148.145', 'dst_port': 443, 'is_spam': False,
        #  'extra': {'raw': '1.653553000\t57.144.148.145\t443\t192.168.1.6\t51801\t43'}}
        hostname=request.data.get('hostname').split('.')[1]
        spam=request.data.get('is_spam')
        userID=request.user.id

        # print(hostname,spam,userID)
        try:
            packetdata=PacketDetail.objects.filter(user=userID,hostname=hostname).first()
            if spam:
                serilizer=packetDetailSerializer(packetdata,data={'is_spam':packetdata.is_spam+1},partial=True)
            else:
                serilizer=packetDetailSerializer(packetdata,data={'not_spam':packetdata.not_spam+1},partial=True)
                print(packetdata)
            if serilizer.is_valid():
                serilizer.save()
            return Response({"credential":True},status=200)
            
        except:
            print("except")
            if spam:
                data={'user':userID,'hostname':hostname,'is_spam':1,'not_spam':0}
            else:
                data={'user':userID,'hostname':hostname,'is_spam':0,'not_spam':1}
            serilizer=packetDetailSerializer(data=data)
            if serilizer.is_valid():
                serilizer.save()
                return Response({"credential":True},status=200)

        return Response({"credential":False},status=200)

class PacketAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Fetch packet data from DB, analyze spam vs non-spam counts, generate graph
        """

        # Fetch packet data for the current user (you can add filters like hostname, etc.)
        packets = PacketDetail.objects.filter(user=request.user)

        # Calculate the total number of spam and non-spam packets
        total_spam = packets.aggregate(total_spam=F('is_spam')).get('total_spam', 0)
        total_non_spam = packets.aggregate(total_non_spam=F('not_spam')).get('total_non_spam', 0)

        # Calculate accuracy (optional, based on your own logic)
        total = total_spam + total_non_spam
        accuracy = (total_non_spam / total) * 100 if total else 0  # Avoid division by zero

        # Generate Graph using Matplotlib
        fig, ax = plt.subplots(figsize=(6, 4))

        categories = ['Spam', 'Non-Spam']
        values = [total_spam, total_non_spam]

        ax.bar(categories, values, color=['red', 'green'])
        ax.set_title('Spam vs Non-Spam Packet Analysis')
        ax.set_ylabel('Packet Count')

        # Convert the graph to an image (base64 encoding to send to the frontend)
        img_buf = BytesIO()
        plt.savefig(img_buf, format='png')
        img_buf.seek(0)
        img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')

        # Prepare the response payload (including graph and accuracy)
        report = {
            "total_spam": total_spam,
            "total_non_spam": total_non_spam,
            "accuracy": accuracy,
            "graph": img_base64,
        }

        return Response(report)


# only respone returned
# class spam_view(APIView):
#     def get(self, request):
#         time.sleep(1)  # simulate some processing delay
#         return Response({"message":"Spam requests sent"},status=200)

# class attack_sim(APIView):
#     def get(self, request):
#         if request.headers.get("X-FYP-MALICIOUS") == "1":
#             return JsonResponse({"status": "attack"})
#         return JsonResponse({"status": "ok"})
















# # views.py — Step-1 Authentication (Django + DRF + SimpleJWT), hashed OTP
# from datetime import timedelta
# from django.db.models import Count, Q
# from django.utils import timezone
# from django.contrib.auth import authenticate
# from django.contrib.auth.hashers import make_password, check_password
# from django.db import transaction
# from .helper_method import generate_otp_code
# from rest_framework.views import APIView
# from rest_framework.generics import ListAPIView, RetrieveAPIView

# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from rest_framework import status

# from rest_framework_simplejwt.tokens import RefreshToken

# from .models import User, VerificationCode , PrivacyScan, PrivacyIssue, Report
# from .serializers import (
#     VerificationCodeSerializer,
#     UserSerializer,
#     LoginSerializer,
#     LogoutSerializer,
#     PrivacyScanSerializer,
#     PrivacyIssueSerializer,
#     ReportSerializer,
#     DashboardSummarySerializer,
#     UserSerializer1,

# )
# from rest_framework.decorators import permission_classes
# from rest_framework.permissions import IsAuthenticated
# # from .utils import generate_otp_code  # returns a short code (string/number)


# class RegisterUser(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         email = (request.data.get("email") or "").strip().lower()
#         username = request.data.get("username")
#         password = request.data.get("password")

#         if not email or not username or not password:
#             return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

#         # Uniqueness checks
#         if User.objects.filter(email=email).exists():
#             return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)
#         if User.objects.filter(username=username).exists():
#             return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

#         # Prepare OTP record for signup verification
#         otp_code = generate_otp_code()
#         with transaction.atomic():
#             vc, created = VerificationCode.objects.update_or_create(
#                 email=email,
#                 purpose="signup_email",
#                 defaults={
#                     "code_hash": make_password(otp_code),                     # hash for storage
#                     "expires_at": timezone.now() + timedelta(minutes=5),
#                     "meta_json": {
#                         "username": username,
#                         "password": make_password(password),                  # (keeping your current pattern)
#                     },
#                     "attempts": 0,
#                     "consumed_at": None,
#                 },
#             )

#         # TODO: send email with otp_code
#         print(otp_code)  # dev log—remove in prod
#         return Response({"id": vc.id, "OTP_SENT": True}, status=status.HTTP_201_CREATED)


# class VerifyCode(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         """
#         Verify OTP for 'signup_email' or 'login_2fa'
#         Body: { "id": "<verification_id>", "otp": "<code>" }
#         """
#         otp = request.data.get("otp")
#         vc_id = request.data.get("id")

#         if not otp or not vc_id:
#             return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

#         vc = VerificationCode.objects.filter(id=vc_id).first()
#         if not vc:
#             return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

#         # guards
#         if vc.expires_at and vc.expires_at < timezone.now():
#             return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
#         if vc.consumed_at:
#             return Response({"error": "OTP has already been consumed"}, status=status.HTTP_400_BAD_REQUEST)
#         if vc.attempts is not None and vc.attempts >= 2:
#             return Response({"error": "Maximum attempts reached"}, status=status.HTTP_400_BAD_REQUEST)
#         if not check_password(otp, vc.code_hash):  # hashed compare
#             vc.attempts = (vc.attempts or 0) + 1
#             vc.save(update_fields=["attempts"])
#             return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

#         purpose = vc.purpose
#         try:
#             if purpose == "signup_email":
#                 with transaction.atomic():
#                     meta = vc.meta_json or {}
#                     user_payload = {
#                         "email": vc.email,
#                         "username": meta.get("username"),
#                         "password": meta.get("password"),  # already hashed
#                         "email_verified": True,
#                         "two_factor_enabled": False,
#                     }
#                     user_ser = UserSerializer(data=user_payload)
#                     if user_ser.is_valid():
#                         user_ser.save()
#                         vc.delete()
#                         return Response({"message": "User created successfully"}, status=status.HTTP_200_OK)
#                     return Response(user_ser.errors, status=status.HTTP_400_BAD_REQUEST)

#             elif purpose == "login_2fa":
#                 user = vc.user
#                 if not user:
#                     return Response({"error": "Invalid verification context"}, status=400)

#                 vc.consume()  # ✅ mark OTP used

#                 refresh = RefreshToken.for_user(user)
#                 return Response(
#                     {"token": {"refresh": str(refresh), "access": str(refresh.access_token)}},
#                     status=200,
#                 )

#             else:
#                 return Response({"error": "Unsupported purpose"}, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#     def put(self, request):
#         """
#         Reset password confirmation
#         Body: { "id": "<verification_id>", "otp": "<code>", "password": "<new_password>" }
#         """
#         otp = request.data.get("otp")
#         vc_id = request.data.get("id")
#         new_password = request.data.get("password")

#         if not otp or not vc_id or not new_password:
#             return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

#         vc = VerificationCode.objects.filter(id=vc_id).first()
#         if not vc:
#             return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

#         # guards
#         if vc.expires_at and vc.expires_at < timezone.now():
#             return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
#         if vc.consumed_at:
#             return Response({"error": "OTP has already been consumed"}, status=status.HTTP_400_BAD_REQUEST)
#         if vc.attempts is not None and vc.attempts >= 2:
#             return Response({"error": "Maximum attempts reached"}, status=status.HTTP_400_BAD_REQUEST)
#         if not check_password(otp, vc.code_hash):  # <-- previously was plain compare
#             vc.attempts = (vc.attempts or 0) + 1
#             vc.save(update_fields=["attempts"])
#             return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

#         # change password
#         try:
#             user = User.objects.filter(email=vc.email).first()
#             if not user:
#                 return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

#             user.set_password(new_password)
#             user.save(update_fields=["password"])

#             vc.delete()
#             return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class Reset_Password(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         """
#         Start password reset
#         Body: { "username": "<user_username>" }
#         """
#         username = request.data.get("username")
#         user = User.objects.filter(username=username).first()
#         if user is None:
#             return Response({"error": "User does not exist"}, status=status.HTTP_400_BAD_REQUEST)

#         otp_code = generate_otp_code()

#         # ✅ upsert to keep at most one active reset code per (email, purpose)
#         with transaction.atomic():
#             vc, created = VerificationCode.objects.update_or_create(
#                 email=user.email,
#                 purpose="reset_password",
#                 defaults={
#                     "user": user,                                          # or user if FK is to User object
#                     "code_hash": make_password(otp_code),
#                     "expires_at": timezone.now() + timedelta(minutes=5),
#                     "meta_json": {"username": username},
#                     "attempts": 0,
#                     "consumed_at": None,
#                 },
#             )

#         # TODO: send email with otp_code
#         print(otp_code)  # dev log

#         # Mask email for UX (same as your code)
#         try:
#             at_idx = user.email.index("@")
#             masked = f"{user.email[:max(0, at_idx-2)]}**{user.email[at_idx:]}"
#         except Exception:
#             masked = user.email

#         return Response({"id": vc.id, "OTP_SENT": True, "email": masked}, status=status.HTTP_201_CREATED)


# # class LoginView(APIView):
# #     permission_classes = [AllowAny]

# #     def post(self, request):
# #         """
# #         Login:
# #         - If 2FA enabled → send OTP and return verification id
# #         - Else → return JWT tokens
# #         """
# #         ser = LoginSerializer(data=request.data)
# #         if not ser.is_valid():
# #             return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

# #         username = request.data.get("username")
# #         password = request.data.get("password")

# #         user = User.objects.filter(username=username).first()
# #         if not user:
# #             return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

# #         if not authenticate(username=username, password=password):
# #             return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

# #         if getattr(user, "two_factor_enabled", False):
# #             otp_code = generate_otp_code()

# #             vc, created = VerificationCode.objects.update_or_create(
# #                 email=user.email,
# #                 purpose=VerificationCode.PURPOSE_LOGIN_2FA,
# #                 defaults={
# #                     "user": user,
# #                     "code_hash": make_password(otp_code),
# #                     "expires_at": timezone.now() + timedelta(minutes=5),
# #                     "attempts": 0,
# #                     "consumed_at": None,
# #                     "meta_json": {"username": user.username},
# #                 }
# #             )

# #             print(otp_code)  # dev only
# #             return Response(
# #                 {"id": vc.id, "OTP_SENT": True},
# #                 status=status.HTTP_201_CREATED
# #             )

# class LoginView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         """
#         Login Flow:
#         - username OR email + password
#         - If 2FA enabled → send OTP (replace existing active OTP safely)
#         - Else → return JWT tokens
#         """

#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         # authenticated user from serializer
#         user = serializer.validated_data["user"]

#         # -----------------------------
#         # 2FA ENABLED
#         # -----------------------------
#         if user.two_factor_enabled:
#             otp_code = generate_otp_code()

#             # IMPORTANT:
#             # One active OTP per (email, purpose)
#             # update_or_create avoids UNIQUE constraint crash
#             verification, _ = VerificationCode.objects.update_or_create(
#                 email=user.email,
#                 purpose=VerificationCode.PURPOSE_LOGIN_2FA,
#                 defaults={
#                     "user": user,
#                     "code_hash": make_password(otp_code),
#                     "expires_at": timezone.now() + timedelta(minutes=5),
#                     "attempts": 0,
#                     "consumed_at": None,
#                     "meta_json": {"username": user.username},
#                 }
#             )

#             # dev only (email/SMS yahan bhejna hota hai)
#             print("LOGIN OTP:", otp_code)

#             return Response(
#                 {
#                     "id": verification.id,
#                     "OTP_SENT": True,
#                     "two_factor": True,
#                 },
#                 status=status.HTTP_201_CREATED,
#             )

#         # -----------------------------
#         # NO 2FA → DIRECT TOKENS
#         # -----------------------------
#         refresh = RefreshToken.for_user(user)
#         return Response(
#             {
#                 "token": {
#                     "refresh": str(refresh),
#                     "access": str(refresh.access_token),
#                 },
#                 "two_factor": False,
#             },
#             status=status.HTTP_200_OK,
#         )
# # class LoginView(APIView):
# #     def post(self, request):
# #         serilizer=LoginSerializer(data=request.data)
# #         if serilizer.is_valid():
            
# #             user=User.objects.filter(username=request.data.get('username'))
# #             # check 2fa enabled
# #             if user.first().two_factor_enabled:
# #                 otp_code = generate_otp_code()
# #                 data={
# #                   'user': user.first().id,
# #                   "email": user.first().email,
# #                   "purpose": "login_2fa",
# #                   "code_hash": otp_code,
# #                   "expires_at": timezone.now() + timedelta(minutes=5),
# #                   "meta_json": {"username": request.data.get('username')},
# #                 }
# #                 serilizer=VerificationCodeSerializer(data=data)

# #                 if serilizer.is_valid():
# #                     serilizer.save()
# #                     print(otp_code)
# #                     return Response({"id":serilizer.data['id'], "OTP_SENT": True}, status=201)
# #                 else:
# #                     return Response(serilizer.errors, status=400)
# #             else:
# #                 refresh = RefreshToken.for_user(user.first())
# #                 return Response({
# #                     "token": {
# #                         "refresh": str(refresh),
# #                         "access": str(refresh.access_token),
# #                     }
# #                 }, status=200)
# #         else:
# #             return Response(serilizer.errors, status=400)

# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         """
#         Logout:
#         Body: { "refresh": "<refresh_token>" }
#         """
#         ser = LogoutSerializer(data=request.data)
#         ser.is_valid(raise_exception=True)

#         try:
#             token = RefreshToken(ser.validated_data["refresh"])
#             token.blacklist()
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


# # dashboard summary view

# class DashboardSummaryView(APIView):
#     """
#     GET /api/dashboard/summary/
#     Purpose: main header block of the dashboard.
#     Includes: user profile, latest scan, recent scans, issue counts, quick-nav.
#     """
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user

#         scans_qs = PrivacyScan.objects.filter(user=user).order_by("-started_at")
#         latest_scan = scans_qs.first()
#         recent_scans = scans_qs[:5]

#         # aggregate open issues (across latest scan or all scans — here we use all)
#         open_issue_count = PrivacyIssue.objects.filter(scan__user=user, status="open").count()
#         sev_qs = (
#             PrivacyIssue.objects.filter(scan__user=user)
#             .values("severity")
#             .annotate(total=Count("id"))
#         )
#         sev_map = {row["severity"]: row["total"] for row in sev_qs}

#         payload = {
#             "user": user,
#             "latest_scan": latest_scan,
#             "recent_scans": recent_scans,
#             "open_issues": open_issue_count,
#             "severity_breakdown": {
#                 "low": sev_map.get("low", 0),
#                 "medium": sev_map.get("medium", 0),
#                 "high": sev_map.get("high", 0),
#                 "critical": sev_map.get("critical", 0),
#             },
#             "nav": {
#                 "scans": "/api/scans/",
#                 "issues": "/api/issues/",
#                 "reports": "/api/reports/",
#                 "start_scan": "/api/scans/start/",
#             },
#         }

#         ser = DashboardSummarySerializer(payload)
#         return Response(ser.data, status=status.HTTP_200_OK)


# class ScanListView(ListAPIView):
#     """
#     GET /api/scans/?status=&source=
#     Lists scans for the authenticated user with optional filters.
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = PrivacyScanSerializer

#     def get_queryset(self):
#         user = self.request.user
#         qs = PrivacyScan.objects.filter(user=user)
#         status_param = self.request.query_params.get("status")
#         source_param = self.request.query_params.get("source")
#         if status_param:
#             qs = qs.filter(status=status_param)
#         if source_param:
#             qs = qs.filter(source__icontains=source_param)
#         return qs.order_by("-started_at")


# class ScanDetailView(RetrieveAPIView):
#     """
#     GET /api/scans/<id>/
#     Retrieves a scan with its issues embedded.
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = PrivacyScanSerializer
#     lookup_url_kwarg = "scan_id"

#     def get_queryset(self):
#         return PrivacyScan.objects.filter(user=self.request.user)


# class StartScanView(APIView):
#     """
#     POST /api/scans/start/
#     Body: { "source": "facebook, google" }  (optional)
#     Creates a 'pending' scan and returns it.
#     In real flow you would kick a Celery task to populate issues, score, etc.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         source = (request.data.get("source") or "").strip()
#         scan = PrivacyScan.objects.create(user=request.user, source=source or "")
#         # TODO: enqueue real analyzer task (celery/redis) → update scan + create issues
#         # For now: mark as running immediately to reflect UI progression
#         scan.status = PrivacyScan.Status.RUNNING
#         scan.save(update_fields=["status"])

#         return Response(PrivacyScanSerializer(scan).data, status=status.HTTP_201_CREATED)


# class IssuesListView(ListAPIView):
#     """
#     GET /api/issues/?scan_id=&status=&severity=&q=
#     Returns paginated list of issues (across all scans or a single scan).
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = PrivacyIssueSerializer

#     def get_queryset(self):
#         user = self.request.user
#         qs = PrivacyIssue.objects.filter(scan__user=user)

#         scan_id = self.request.query_params.get("scan_id")
#         if scan_id:
#             qs = qs.filter(scan_id=scan_id)

#         status_param = self.request.query_params.get("status")
#         if status_param:
#             qs = qs.filter(status=status_param)

#         severity_param = self.request.query_params.get("severity")
#         if severity_param:
#             qs = qs.filter(severity=severity_param)

#         q = self.request.query_params.get("q")
#         if q:
#             qs = qs.filter(
#                 Q(title__icontains=q) |
#                 Q(description__icontains=q) |
#                 Q(category__icontains=q) |
#                 Q(affected_item__icontains=q)
#             )

#         return qs.order_by("-created_at")


# class IssueResolveView(APIView):
#     """
#     POST /api/issues/<id>/resolve/
#     Body: { "action": "resolve" | "ignore" }
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request, issue_id):
#         action = (request.data.get("action") or "resolve").lower()
#         try:
#             issue = PrivacyIssue.objects.get(id=issue_id, scan__user=request.user)
#         except PrivacyIssue.DoesNotExist:
#             return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)

#         if action == "resolve":
#             issue.status = "resolved"
#             issue.resolved_at = timezone.now()
#         elif action == "ignore":
#             issue.status = "ignored"
#             issue.resolved_at = timezone.now()
#         else:
#             return Response({"error": "Unsupported action"}, status=status.HTTP_400_BAD_REQUEST)

#         issue.save(update_fields=["status", "resolved_at"])
#         return Response(PrivacyIssueSerializer(issue).data, status=status.HTTP_200_OK)


# class ReportsListView(ListAPIView):
#     """
#     GET /api/reports/
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = ReportSerializer

#     def get_queryset(self):
#         return Report.objects.filter(user=self.request.user).order_by("-generated_at")


# class ReportDetailView(RetrieveAPIView):
#     """
#     GET /api/reports/<id>/
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = ReportSerializer
#     lookup_url_kwarg = "report_id"

#     def get_queryset(self):
#         return Report.objects.filter(user=self.request.user)

# class UserMeView(APIView):
#     permission_classes = [IsAuthenticated]
#     def get(self, request):
#         users=User.objects.get(id=request.user.id)
#         serilizer=UserSerializer1(users)
#         return Response(serilizer.data, status=200)
    

#     def put(self, request):
#         users = User.objects.filter(username=request.user.username).first()
#         try:
#             if request.data.get('new_password'):
#                 crunt_password = request.data.get('current_password')
#                 if not users.check_password(crunt_password):
#                     return Response({"error": "Current password is incorrect"}, status=400)
#                 password = make_password(request.data.get('new_password'))
                
#                 users.password = password
#                 users.save()
#                 return Response({"success": True}, status=200)
#         except:
#             pass
#         serializer = UserSerializer1(users, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=200)
#         else:
#             return Response(serializer.errors, status=400)
#     def delete(self, request):
#         users=User.objects.get(id=request.user.id)
#         users.delete()
#         return Response({"success":True}, status=200)
    
# class UserPasswordView(APIView):
#     permission_classes = [IsAuthenticated]

#     def put(self, request):
#         current_password = request.data.get("current_password")
#         new_password = request.data.get("new_password")
#         if not current_password or not new_password:
#             return Response({"detail": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
#         u = request.user
#         if not u.check_password(current_password):
#             return Response({"detail": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
#         if len(new_password) < 8:
#             return Response({"detail": "New password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)
#         u.set_password(new_password)
#         u.save(update_fields=["password"])
#         return Response({"message": "Password changed"}, status=status.HTTP_200_OK)


# class PacketView(APIView):
#     # permission_classes = [IsAuthenticated]
#     def post(self, request):
#         print(request.data)
#         return Response({"credential":True},status=200)

