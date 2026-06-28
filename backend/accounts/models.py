# # models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone


class User(AbstractUser):
    """
    Uses default Django USERNAME login.
    Email is stored for OTP delivery and must be unique.
    """
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class VerificationCode(models.Model):
    PURPOSE_SIGNUP = "signup_email"
    PURPOSE_LOGIN_2FA = "login_2fa"
    PURPOSE_RESET = "reset_password"

    PURPOSE_CHOICES = [
        (PURPOSE_SIGNUP, "Signup Email"),
        (PURPOSE_LOGIN_2FA, "Login 2FA"),
        (PURPOSE_RESET, "Reset Password"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="verification_codes",
    )
    email = models.EmailField()
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)

    # Store HASH of OTP (use make_password/check_password)
    code_hash = models.CharField(max_length=128)

    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    meta_json = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["purpose"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["email", "purpose"]),
        ]
        constraints = [
            # One *active* (unconsumed) code per (email, purpose)
            models.UniqueConstraint(
                fields=["email", "purpose"],
                condition=Q(consumed_at__isnull=True),
                name="uq_active_code_per_email_purpose",
            ),
            # purpose ↔ user relation rules
            models.CheckConstraint(
                check=(
                    (Q(purpose="signup_email") & Q(user__isnull=True)) |
                    (Q(purpose__in=["login_2fa", "reset_password"]) & Q(user__isnull=False))
                ),
                name="ck_purpose_user_relation",
            ),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < timezone.now())

    def bump_attempts(self, max_times: int = 2) -> bool:
        self.attempts = (self.attempts or 0) + 1
        self.save(update_fields=["attempts"])
        return self.attempts >= max_times

    def consume(self):
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])

    def __str__(self):
        return f"{self.purpose} for {self.email}"


class Report(models.Model):
    """
    Optional: generated report snapshot.
    You can attach it to a scan later; for now keep it standalone.
    """
    PLATFORM_CHOICES = (
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
        ("thread", "Threads"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    title = models.CharField(max_length=255)
    platform = models.CharField(max_length=30, default="unknown", db_index=True)
  # ✅ ADDED
    generated_at = models.DateTimeField(auto_now_add=True)
    payload_json = models.JSONField(default=dict, blank=True)
    file_url = models.URLField(blank=True, default="")

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["user", "-generated_at"]),
            models.Index(fields=["user", "platform", "-generated_at"]),  # ✅ helpful
        ]

    def __str__(self):
        return f"Report #{self.id} — {self.title}"



class PacketDetail(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hostname = models.CharField(max_length=255)
    not_spam = models.IntegerField()
    is_spam = models.IntegerField()


class PacketEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.CharField(max_length=30, db_index=True)
    is_spam = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "platform", "created_at"]),
        ]




# from django.conf import settings
# from django.contrib.auth.models import AbstractUser
# from django.core.exceptions import ValidationError
# from django.db import models
# from django.db.models import Q
# from django.utils import timezone


# class User(AbstractUser):
#     """
#     Login is with USERNAME (default Django).
#     Email is stored for OTP delivery and uniqueness.
#     """
#     email = models.EmailField(unique=True)
#     email_verified = models.BooleanField(default=False)
#     two_factor_enabled = models.BooleanField(default=False)

#     def save(self, *args, **kwargs):
#         if self.email:
#             self.email = self.email.strip().lower()
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.username


# class VerificationCode(models.Model):
#     PURPOSE_SIGNUP = "signup_email"
#     PURPOSE_LOGIN_2FA = "login_2fa"
#     PURPOSE_RESET = "reset_password"

#     PURPOSE_CHOICES = [
#         (PURPOSE_SIGNUP, "Signup Email"),
#         (PURPOSE_LOGIN_2FA, "Login 2FA"),
#         (PURPOSE_RESET, "Reset Password"),
#     ]

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="verification_codes",
#     )
#     email = models.EmailField()
#     purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)
#     # Store HASH of the OTP (views use make_password/check_password)
#     code_hash = models.CharField(max_length=128)  # pbkdf2 hashes fit
#     expires_at = models.DateTimeField()
#     consumed_at = models.DateTimeField(null=True, blank=True)
#     attempts = models.PositiveSmallIntegerField(default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     meta_json = models.JSONField(null=True, blank=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=["email"]),
#             models.Index(fields=["purpose"]),
#             models.Index(fields=["expires_at"]),
#             models.Index(fields=["email", "purpose"]),
#         ]
#         constraints = [
#             # One *active* (unconsumed) code per (email, purpose)
#             models.UniqueConstraint(
#                 fields=["email", "purpose"],
#                 condition=Q(consumed_at__isnull=True),
#                 name="uq_active_code_per_email_purpose",
#             ),
#             # IMPORTANT: use literal strings inside Meta (not class constants)
#             models.CheckConstraint(
#                 check=(
#                     (Q(purpose="signup_email") & Q(user__isnull=True)) |
#                     (Q(purpose__in=["login_2fa", "reset_password"]) & Q(user__isnull=False))
#                 ),
#                 name="ck_purpose_user_relation",
#             ),
#         ]
#         ordering = ["-created_at"]

#     def save(self, *args, **kwargs):
#         if self.email:
#             self.email = self.email.strip().lower()
#         super().save(*args, **kwargs)

#     @property
#     def is_expired(self) -> bool:
#         return self.expires_at and self.expires_at < timezone.now()

#     def bump_attempts(self, max_times: int = 2) -> bool:
#         """Increment attempts and return whether max reached."""
#         self.attempts = (self.attempts or 0) + 1
#         self.save(update_fields=["attempts"])
#         return self.attempts >= max_times

#     def consume(self):
#         self.consumed_at = timezone.now()
#         self.save(update_fields=["consumed_at"])

#     def __str__(self):
#         return f"{self.purpose} for {self.email}"


# class Item(models.Model):
#     owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="items")
#     name = models.CharField(max_length=255)  # PLAINTEXT filename (UI)
#     current_revision = models.ForeignKey("ItemVersion", null=True, blank=True,
#                                          on_delete=models.SET_NULL, related_name="+")
#     version_limit = models.PositiveIntegerField(default=5)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         indexes = [models.Index(fields=["owner", "-updated_at"])]

#     def __str__(self):
#         return f"Item {self.name} (owner={self.owner_id})"


# class ItemVersion(models.Model):
#     item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="versions")
#     version_no = models.PositiveIntegerField()  # 1..N (unique per item)
#     previous_version = models.ForeignKey("self", null=True, blank=True,
#                                          on_delete=models.SET_NULL, related_name="next_versions")

#     # File content (ciphertext)
#     file = models.BinaryField()
#     cipher = models.CharField(max_length=32, default="AES-256-GCM")
#     cipher_nonce = models.BinaryField()              # 12 bytes
#     sha256_cipher = models.CharField(max_length=64)  # exact hex length

#     # Encrypted filename (per-version)
#     filename_ct = models.BinaryField(null=True, blank=True)
#     filename_nonce = models.BinaryField(null=True, blank=True)  # 12 bytes if used

#     created_at = models.DateTimeField(auto_now_add=True)
#     deleted_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=["item", "version_no"], name="uq_item_version_no"),
#         ]
#         indexes = [models.Index(fields=["item", "deleted_at", "version_no"])]
#         ordering = ["item_id", "version_no"]

#     def clean(self):
#         if self.cipher.upper().startswith("AES") and self.cipher_nonce and len(self.cipher_nonce) != 12:
#             raise ValidationError("AES-GCM nonce must be 12 bytes.")
#         if self.sha256_cipher and len(self.sha256_cipher) != 64:
#             raise ValidationError("sha256_cipher must be a 64-char hex string.")
#         if self.filename_nonce and len(self.filename_nonce) != 12:
#             raise ValidationError("filename_nonce must be 12 bytes.")

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)

#     def __str__(self):
#         return f"ItemVersion item={self.item_id} v{self.version_no}"


# class ItemVersionActivity(models.Model):
#     # FIX: this should point to ItemVersion, not Item
#     version = models.ForeignKey(               # <-- FIX
#         ItemVersion,                           # <-- FIX
#         on_delete=models.CASCADE,
#         related_name="activities",
#         db_index=True,
#     )
#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,   # user delete ho to log rahe
#         null=True, blank=True,
#         db_index=True,
#     )
#     task = models.CharField(max_length=40)  # e.g. "VERSION_CREATED", "CT_DOWNLOADED"
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True)

#     class Meta:
#         indexes = [
#             models.Index(fields=["version", "-created_at"]),
#             models.Index(fields=["user", "-created_at"]),
#         ]

#     def __str__(self):
#         return f"{self.task} v{self.version_id} by {self.user_id} @ {self.created_at}"


# # ===============================
# # STEP-2 ADD: Dashboard domain
# # ===============================

# class PrivacyScan(models.Model):  # STEP-2 ADD
#     class Status(models.TextChoices):
#         PENDING = "pending", "Pending"
#         RUNNING = "running", "Running"
#         COMPLETED = "completed", "Completed"
#         FAILED = "failed", "Failed"

#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="privacy_scans")
#     source = models.CharField(max_length=100, blank=True, default="")  # e.g. "facebook, google"
#     started_at = models.DateTimeField(auto_now_add=True)
#     completed_at = models.DateTimeField(null=True, blank=True)
#     status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
#     score = models.PositiveIntegerField(null=True, blank=True)  # 0-100 overall privacy score
#     summary = models.TextField(blank=True, default="")
#     findings_count = models.PositiveIntegerField(default=0)
#     stats_json = models.JSONField(default=dict, blank=True)  # arbitrary counters (by category, severity…)

#     class Meta:
#         ordering = ["-started_at"]
#         indexes = [
#             models.Index(fields=["user", "-started_at"]),
#             models.Index(fields=["status"]),
#         ]

#     def __str__(self):
#         return f"Scan #{self.id} — {self.user} — {self.status}"

#     # convenience for workers to keep count in sync
#     def recompute_findings_count(self):
#         count = self.issues.count()
#         if count != self.findings_count:
#             self.findings_count = count
#             self.save(update_fields=["findings_count"])


# class PrivacyIssue(models.Model):  # STEP-2 ADD
#     class Severity(models.TextChoices):
#         LOW = "low", "Low"
#         MEDIUM = "medium", "Medium"
#         HIGH = "high", "High"
#         CRITICAL = "critical", "Critical"

#     class IssueStatus(models.TextChoices):
#         OPEN = "open", "Open"
#         RESOLVED = "resolved", "Resolved"
#         IGNORED = "ignored", "Ignored"

#     scan = models.ForeignKey(PrivacyScan, on_delete=models.CASCADE, related_name="issues")
#     category = models.CharField(max_length=100)  # e.g. "Data Exposure", "Weak Settings"
#     title = models.CharField(max_length=255)
#     description = models.TextField()
#     severity = models.CharField(max_length=10, choices=Severity.choices)
#     affected_item = models.CharField(max_length=255, blank=True, default="")  # e.g. "Public profile picture"
#     evidence_json = models.JSONField(default=dict, blank=True)
#     status = models.CharField(max_length=10, choices=IssueStatus.choices, default=IssueStatus.OPEN)
#     recommendation_text = models.TextField(blank=True, default="")
#     recommendation_fix_json = models.JSONField(default=dict, blank=True)  # step-by-step fix, deep links, etc.
#     created_at = models.DateTimeField(auto_now_add=True)
#     resolved_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         ordering = ["-created_at"]
#         indexes = [
#             models.Index(fields=["scan", "severity", "status", "-created_at"]),
#             models.Index(fields=["category"]),
#         ]

#     def __str__(self):
#         return f"[{self.severity}] {self.title}"


# class Report(models.Model):  # STEP-2 ADD
#     """
#     Optional: generated report snapshot from a scan.
#     Can be rendered to PDF later; for now store JSON payload & a title.
#     """
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
#     scan = models.ForeignKey(PrivacyScan, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
#     title = models.CharField(max_length=255)
#     generated_at = models.DateTimeField(auto_now_add=True)
#     payload_json = models.JSONField(default=dict, blank=True)  # summary, key issues, recommendations
#     file_url = models.URLField(blank=True, default="")  # if/when you export a PDF and host it

#     class Meta:
#         ordering = ["-generated_at"]
#         indexes = [
#             models.Index(fields=["user", "-generated_at"]),
#         ]

#     def __str__(self):
#         return f"Report #{self.id} — {self.title}"
