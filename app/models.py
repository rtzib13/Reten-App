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
        return f"{self.title} ({self.city})"


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
