from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import VerificationCode, Report , PacketDetail

User = get_user_model()


class VerificationCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationCode
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    """
    Used for creating user after signup OTP verification.
    NOTE: In your current flow, password is already hashed in meta_json.
    So we assign it directly (not using set_password).
    """
    class Meta:
        model = User
        fields = ("email", "username", "password", "email_verified", "two_factor_enabled")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password is not None:
            user.password = password  # already hashed
        user.save()
        return user


class UserSerializer1(serializers.ModelSerializer):
    """
    Profile serializer (read/update).
    Email/username read-only as per your requirement.
    """
    class Meta:
        model = User
        fields = ("username", "email", "two_factor_enabled", "email_verified", "password")
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "email": {"read_only": True},
            "email_verified": {"read_only": True},
            "username": {"read_only": True},
        }

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login_value = (attrs.get("username") or "").strip()
        password = attrs.get("password")

        if not login_value or not password:
            raise serializers.ValidationError({"non_field_errors": ["Missing credentials"]})

        # username OR email
        if "@" in login_value:
            user = User.objects.filter(email__iexact=login_value).first()
        else:
            user = User.objects.filter(username=login_value).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError({"non_field_errors": ["Invalid credentials"]})

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "title", "platform", "generated_at", "payload_json", "file_url"]
        read_only_fields = ["id", "generated_at"]

class packetDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PacketDetail
        fields = "__all__"








# # serilizer.py  — DRF serializers (minimal, sirf views ki zaroorat ke mutabiq)
# from rest_framework import serializers as serializer
# from .models import User, VerificationCode ,PrivacyScan, PrivacyIssue, Report
# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# User = get_user_model()

# class VerificationCodeSerializer(serializer.ModelSerializer):
#     class Meta:
#         model = VerificationCode
#         fields = "__all__"


# class UserSerializer(serializer.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ("email", "username", "password", "email_verified", "two_factor_enabled")
#         extra_kwargs = {"password": {"write_only": True}}

#     def create(self, validated_data):
#         # Views already hashed password in meta; dobara hash NAHIN kar rahe
#         password = validated_data.pop("password", None)
#         user = User(**validated_data)
#         if password is not None:
#             user.password = password
#         user.save()
#         return user


# class UserSerializer1(serializer.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['username','email','two_factor_enabled','email_verified','password']
#         extra_kwargs = {'password': {'write_only': True},
#                         'email': {'read_only': True},
#                         'email_verified': {'read_only': True},
#                         'username': {'read_only': True},
#                         }
#         def update(self, instance, validated_data):
#             password = validated_data.pop("password", None)
#             # baki fields update karo
#             for attr, value in validated_data.items():
#                 setattr(instance, attr, value)

#             # agar password aya ho to hash kar ke set karo
#             if password:
#                 instance.set_password(password)
#             instance.save()
#             return instance


# class LoginSerializer(serializers.Serializer):
#     username = serializers.CharField()
#     password = serializers.CharField(write_only=True)

#     def validate(self, attrs):
#         login_value = attrs["username"]
#         password = attrs["password"]

#         if "@" in login_value:
#             user = User.objects.filter(email__iexact=login_value).first()
#         else:
#             user = User.objects.filter(username=login_value).first()

#         if not user or not user.check_password(password):
#             raise serializers.ValidationError(
#                 {"non_field_errors": ["Invalid credentials"]}
#             )

#         attrs["user"] = user
#         return attrs



# class LogoutSerializer(serializer.Serializer):
#     refresh = serializer.CharField()

# class PrivacyIssueSerializer(serializer.ModelSerializer):
#     class Meta:
#         model = PrivacyIssue
#         fields = (
#             "id",
#             "scan",
#             "category",
#             "title",
#             "description",
#             "severity",
#             "affected_item",
#             "evidence_json",
#             "status",
#             "recommendation_text",
#             "recommendation_fix_json",
#             "created_at",
#             "resolved_at",
#         )
#         read_only_fields = ("id", "created_at", "resolved_at", "scan")


# class PrivacyScanSerializer(serializer.ModelSerializer):
#     issues = PrivacyIssueSerializer(many=True, read_only=True)

#     class Meta:
#         model = PrivacyScan
#         fields = (
#             "id",
#             "user",
#             "source",
#             "started_at",
#             "completed_at",
#             "status",
#             "score",
#             "summary",
#             "findings_count",
#             "stats_json",
#             "issues",
#         )
#         read_only_fields = ("id", "user", "started_at", "completed_at", "status", "findings_count")


# class ReportSerializer(serializer.ModelSerializer):
#     scan = PrivacyScanSerializer(read_only=True)

#     class Meta:
#         model = Report
#         fields = ("id", "title", "generated_at", "payload_json", "file_url", "scan")
#         read_only_fields = ("id", "generated_at", "scan")


# class DashboardSummarySerializer(serializer.Serializer):
#     """
#     Aggregated payload for the main dashboard header/overview.
#     """
#     # user profile block
#     user = serializer.SerializerMethodField()

#     # scan overview
#     latest_scan = PrivacyScanSerializer(read_only=True)
#     recent_scans = PrivacyScanSerializer(many=True, read_only=True)

#     # issue aggregates
#     open_issues = serializer.IntegerField()
#     severity_breakdown = serializer.DictField()  # {"low": 1, "medium": 2, ...}

#     # quick-nav
#     nav = serializer.DictField()  # endpoints for front-end to hit

#     def get_user(self, obj):
#         u = obj["user"]
#         return {
#             "username": u.username,
#             "email": u.email,
#             "email_verified": getattr(u, "email_verified", False),
#             "two_factor_enabled": getattr(u, "two_factor_enabled", False),
#         }