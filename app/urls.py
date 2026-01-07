from django.urls import path
from . import views
from .views import (
    ReportListView,
    ReportCreateView,
    ReportUpdateView,
    ReportDeleteView,
    ModerationDashboardView,
)

urlpatterns = [
    path("api/signup/", views.api_signup, name="api-signup"),
    path("api/login/", views.api_login, name="api-login"),

    # Auth
    path("signup/", views.signup_view, name="signup"),

    # Report list (home page)
    path("", ReportListView.as_view(), name="report-list"),

    # Create a new report
    path("report/new/", ReportCreateView.as_view(), name="report-create"),

    # Report detail (view + comments)
    path("report/<int:pk>/", views.report_detail_view, name="report-detail"),

    # Update / delete (owner only)
    path("report/<int:pk>/edit/", ReportUpdateView.as_view(), name="report-update"),
    path("report/<int:pk>/delete/", ReportDeleteView.as_view(), name="report-delete"),

    # Confirm / unconfirm a report
    path("report/<int:pk>/confirm/", views.confirm_report_view, name="report-confirm"),
    path("report/<int:pk>/unconfirm/", views.unconfirm_report_view, name="report-unconfirm"),

    # Moderator dashboard + actions
    path("moderation/", ModerationDashboardView.as_view(), name="mod-dashboard"),
    path("moderation/<int:pk>/verify/", views.verify_report_view, name="report-verify"),
    path("moderation/<int:pk>/resolve/", views.resolve_report_view, name="report-resolve"),
]
