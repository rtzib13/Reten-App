import json

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Q

from rest_framework.authtoken.models import Token

from .models import RoadblockReport, RoadblockComment, RoadblockConfirmation, UserProfile, EmailVerificationToken
from .forms import RoadblockReportForm, RoadblockCommentForm, RoadblockFilterForm, ProfileLocationForm, ProfileContactForm


# ---------- TEMPLATE AUTH (LOCAL DJANGO) ----------
@login_required
def edit_location(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileLocationForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("report-list")
    else:
        form = ProfileLocationForm(instance=profile)

    return render(request, "roadblocks/edit_location.html", {"form": form})

@login_required
def edit_contact_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileContactForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Contact info saved.")
            return redirect("edit-contact")
    else:
        form = ProfileContactForm(instance=profile)

    return render(request, "roadblocks/edit_contact.html", {"form": form, "profile": profile})

@login_required
def send_verification_email_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.email:
        return redirect("edit-contact")

    token_obj, _ = EmailVerificationToken.objects.get_or_create(user=request.user)

    verify_url = request.build_absolute_uri(
        reverse_lazy("verify-email", kwargs={"token": str(token_obj.token)})
    )

    send_mail(
        subject="Verify your Roadblocks account",
        message=f"Click this link to verify your account:\n\n{verify_url}\n\nThis link expires in 24 hours.",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[profile.email],
        fail_silently=False,
    )

    return redirect("edit-contact")

def verify_email_view(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)

    if token_obj.is_expired():
        return HttpResponseBadRequest("Verification link expired. Please request a new one.")

    profile, _ = UserProfile.objects.get_or_create(user=token_obj.user)
    profile.is_verified = True
    profile.save()

    token_obj.delete()  # one-time use

    return render(request, "roadblocks/verify_success.html")

def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("report-list")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})


# ---------- API AUTH (GITHUB PAGES SAFE) ----------
@csrf_exempt
@require_POST
def api_signup(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return JsonResponse({"detail": "username and password required"}, status=400)

    from django.contrib.auth.models import User
    if User.objects.filter(username=username).exists():
        return JsonResponse({"detail": "Username already taken"}, status=400)

    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)

    return JsonResponse(
        {"detail": "Account created", "token": token.key},
        status=201,
    )


@csrf_exempt
@require_POST
def api_login(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid username or password"}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    return JsonResponse(
        {"detail": "Login success", "token": token.key},
        status=200,
    )


# ---------- MIXINS ----------
class OwnerOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return obj.owner == self.request.user


# ---------- REPORT LIST ----------
class ReportListView(LoginRequiredMixin, ListView):
    model = RoadblockReport
    template_name = "roadblocks/report_list.html"
    context_object_name = "reports"

    def get_queryset(self):
        qs = RoadblockReport.objects.all().order_by("-created_at")

        # --- Location filter: only show reports in my state ---
        profile = getattr(self.request.user, "profile", None)

        if not profile or not profile.state:
            return RoadblockReport.objects.none()

        qs = qs.filter(state__iexact=profile.state)

        form = RoadblockFilterForm(self.request.GET)
        if form.is_valid():
            city = form.cleaned_data.get("city", "").strip()
            severity = form.cleaned_data.get("severity", "")
            status = form.cleaned_data.get("status", "")
            verified_only = form.cleaned_data.get("verified_only", False)

            # NOTE: this city filter narrows within the user's state
            if city:
                qs = qs.filter(city__icontains=city)
            if severity:
                qs = qs.filter(severity=severity)
            if status:
                qs = qs.filter(status=status)
            if verified_only:
                qs = qs.filter(Q(verified=True) | Q(owner__profile__is_verified=True))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = RoadblockFilterForm(self.request.GET)

        # handy flag so you can show a message in template
        profile = getattr(self.request.user, "profile", None)
        ctx["needs_location"] = (not profile or not profile.state)

        return ctx


# ---------- REPORT DETAIL ----------
@login_required
def report_detail_view(request, pk):
    report = get_object_or_404(RoadblockReport, pk=pk)

    if request.method == "POST":
        comment_form = RoadblockCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.owner = request.user
            comment.report = report
            comment.save()
            return redirect("report-detail", pk=pk)
    else:
        comment_form = RoadblockCommentForm()

    already_confirmed = RoadblockConfirmation.objects.filter(
        report=report,
        user=request.user,
    ).exists()

    confirmation_count = report.confirmations.count()

    return render(
        request,
        "roadblocks/report_detail.html",
        {
            "report": report,
            "comment_form": comment_form,
            "already_confirmed": already_confirmed,
            "confirmation_count": confirmation_count,
        },
    )

@login_required
@require_POST
def delete_comment_view(request, comment_id):
    comment = get_object_or_404(RoadblockComment, pk=comment_id)

    # Only the owner of the comment can delete it
    if comment.owner_id != request.user.id:
        return HttpResponseForbidden("You can only delete your own comment.")

    report_id = comment.report_id
    comment.delete()
    return redirect("report-detail", pk=report_id)


@login_required
def confirm_report_view(request, pk):
    report = get_object_or_404(RoadblockReport, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.is_verified:
        return HttpResponseForbidden("You must verify your account before confirming reports.")

    if report.owner_id == request.user.id:
        return HttpResponseForbidden("You cannot confirm your own report.")
    
    RoadblockConfirmation.objects.get_or_create(
        report=report,
        user=request.user,
    )
    return redirect("report-detail", pk=pk)


@login_required
def unconfirm_report_view(request, pk):
    report = get_object_or_404(RoadblockReport, pk=pk)
    RoadblockConfirmation.objects.filter(
        report=report,
        user=request.user,
    ).delete()
    return redirect("report-detail", pk=pk)


# ---------- CRUD ----------
class ReportCreateView(LoginRequiredMixin, CreateView):
    model = RoadblockReport
    form_class = RoadblockReportForm
    template_name = "roadblocks/report_form.html"
    success_url = reverse_lazy("report-list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ReportUpdateView(LoginRequiredMixin, OwnerOnlyMixin, UpdateView):
    model = RoadblockReport
    form_class = RoadblockReportForm
    template_name = "roadblocks/report_form.html"
    success_url = reverse_lazy("report-list")


class ReportDeleteView(LoginRequiredMixin, OwnerOnlyMixin, DeleteView):
    model = RoadblockReport
    template_name = "roadblocks/report_confirm_delete.html"
    success_url = reverse_lazy("report-list")


# ---------- MODERATION ----------
class ModerationDashboardView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "roadblocks.can_verify_report"
    model = RoadblockReport
    template_name = "roadblocks/mod_dashboard.html"
    context_object_name = "reports"

    def get_queryset(self):
        return RoadblockReport.objects.all().order_by("status", "-created_at")


@login_required
def verify_report_view(request, pk):
    report = get_object_or_404(RoadblockReport, pk=pk)
    if not request.user.has_perm("roadblocks.can_verify_report"):
        return redirect("report-list")

    report.verified = True
    report.save()
    return redirect("mod-dashboard")


@login_required
def resolve_report_view(request, pk):
    report = get_object_or_404(RoadblockReport, pk=pk)
    if not request.user.has_perm("roadblocks.can_resolve_report"):
        return redirect("report-list")

    report.status = "RESOLVED"
    report.save()
    return redirect("mod-dashboard")
