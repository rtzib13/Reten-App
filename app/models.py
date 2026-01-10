import uuid
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User


class RoadblockReport(models.Model):
    SEVERITY_CHOICES = [
        ("LOW", "Low"),
        ("MED", "Medium"),
        ("HIGH", "High"),
    ]
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("RESOLVED", "Resolved"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roadblock_reports")
    title = models.CharField(max_length=80)
    description = models.TextField()
    road_name = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=2, null=True, blank=True)


    severity = models.CharField(max_length=4, choices=SEVERITY_CHOICES, default="LOW")
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="ACTIVE")
    verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("can_verify_report", "Can verify roadblock reports"),
            ("can_resolve_report", "Can resolve roadblock reports"),
        ]

    def __str__(self):
        return f"{self.title} ({self.city}, {self.state})"


class RoadblockComment(models.Model):
    report = models.ForeignKey(RoadblockReport, on_delete=models.CASCADE, related_name="comments")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roadblock_comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.owner.username} on {self.report.id}"


class RoadblockConfirmation(models.Model):
    report = models.ForeignKey(RoadblockReport, on_delete=models.CASCADE, related_name="confirmations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roadblock_confirmations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["report", "user"], name="unique_confirmation_per_user")
        ]

    def __str__(self):
        return f"{self.user.username} confirmed {self.report.id}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # location
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=2, blank=True)

    # contact
    email = models.EmailField(blank=True)      # profile email (can differ from User.email if you want)
    phone = models.CharField(max_length=20, blank=True)

    # verification
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} profile"
    
class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > (self.created_at + timedelta(hours=24))

    def __str__(self):
        return f"Email token for {self.user.username}"