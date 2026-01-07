import json

from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from rest_framework.authtoken.models import Token

from .models import RoadblockReport, RoadblockComment, RoadblockConfirmation
from .forms import RoadblockReportForm, RoadblockCommentForm, RoadblockFilterForm


# ---------- TEMPLATE AUTH (LOCAL DJANGO) ----------
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

        form = RoadblockFilterForm(self.request.GET)
        if form.is_valid():
            city = form.cleaned_data.get("city", "").strip()
            severity = form.cleaned_data.get("severity", "")
            status = form.cleaned_data.get("status", "")
            verified_only = form.cleaned_data.get("verified_only", False)

            if city:
                qs = qs.filter(city__icontains=city)
            if severity:
                qs = qs.filter(severity=severity)
            if status:
                qs = qs.filter(status=status)
            if verified_only:
                qs = qs.filter(verified=True)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = RoadblockFilterForm(self.request.GET)
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
def confirm_report_view(request, pk):
    report = get_object_or_404(RoadblockReport, pk=pk)
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
