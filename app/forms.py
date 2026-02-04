from django import forms
from .models import RoadblockReport, RoadblockComment, UserProfile

US_STATES = [
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
]



class RoadblockReportForm(forms.ModelForm):
    state = forms.ChoiceField(choices=US_STATES)
    
    class Meta:
        model = RoadblockReport
        fields = ["title", "description", "road_name","nearby_place", "city", "state", "severity"]

    def clean_title(self):
        t = self.cleaned_data["title"].strip()
        if len(t) < 3:
            raise forms.ValidationError("Title must be at least 3 characters.")
        return t

    def clean_city(self):
        c = self.cleaned_data["city"].strip()
        if c == " ":
            raise forms.ValidationError("City is required.")
        return c
    
    def clean_state(self):
        state = self.cleaned_data["state"]

        if not state.replace(" ", "").isalpha():
            raise forms.ValidationError(
                "State must contain letters only."
            )

        return state



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

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
}

class ProfileLocationForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["city", "state"]

    def clean_state(self):
        state = self.cleaned_data["state"].strip().upper()

        # must be letters only
        if not state.isalpha():
            raise forms.ValidationError("State must contain letters only.")

        # must be exactly 2 letters
        if len(state) != 2:
            raise forms.ValidationError("State must be 2 letters (ex: MS).")

        # must be a real US state
        if state not in US_STATES:
            raise forms.ValidationError("Enter a valid US state abbreviation.")

        return state

    def clean_city(self):
        return self.cleaned_data["city"].strip()
        return city

class ProfileContactForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["email", "phone"]

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        return phone