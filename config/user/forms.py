from django import forms
from django.contrib.auth.models import User
from user.models import IstifadeciProfil
from regions.models import Region
from django.core.exceptions import ValidationError

class QeydiyyatForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Şifrə")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Şifrənin təkrarı")
    bolge = forms.ModelChoiceField(queryset=Region.objects.all(), label="Bölgə")

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_password2(self):
        pw1 = self.cleaned_data.get("password")
        pw2 = self.cleaned_data.get("password2")
        if pw1 != pw2:
            raise ValidationError("Şifrələr eyni deyil!")
        return pw2
