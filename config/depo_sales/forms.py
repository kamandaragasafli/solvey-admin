from django import forms
from django.utils import timezone

from .models import UploadedReport


class UploadedReportForm(forms.ModelForm):
    class Meta:
        model = UploadedReport
        fields = ["depo", "report_date", "file"]
        widgets = {
            "depo": forms.Select(attrs={"class": "form-select"}),
            "report_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "depo": "Depo",
            "report_date": "Tarix",
            "file": "Excel faylı (.xlsx)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["depo"].empty_label = "Depo seçin"
        self.fields["depo"].required = True
        self.fields["report_date"].required = True
        self.fields["report_date"].input_formats = ["%Y-%m-%d"]
        if not self.is_bound and not self.initial.get("report_date"):
            self.initial["report_date"] = timezone.localdate()

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith((".xlsx", ".xlsm")):
            raise forms.ValidationError("Yalnız .xlsx və ya .xlsm faylı qəbul olunur.")
        return f
