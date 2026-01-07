from django import forms
from .models import RoadblockReport, RoadblockComment


class RoadblockReportForm(forms.ModelForm):
    class Meta:
        model = RoadblockReport
        fields = ["title", "description", "road_name", "city", "severity"]

    def clean_title(self):
        t = self.cleaned_data["title"].strip()
        if len(t) < 3:
            raise forms.ValidationError("Title must be at least 3 characters.")
        return t

    def clean_city(self):
        c = self.cleaned_data["city"].strip()
        if c == "":
            raise forms.ValidationError("City is required.")
        return c


class RoadblockCommentForm(forms.ModelForm):
    class Meta:
        model = RoadblockComment
        fields = ["text"]

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if len(text) < 2:
            raise forms.ValidationError("Comment must be at least 2 characters.")
        return text


class RoadblockFilterForm(forms.Form):
    city = forms.CharField(required=False)
    severity = forms.ChoiceField(
        required=False,
        choices=[("", "Any")] + RoadblockReport.SEVERITY_CHOICES,
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Any")] + RoadblockReport.STATUS_CHOICES,
    )
    verified_only = forms.BooleanField(required=False)
