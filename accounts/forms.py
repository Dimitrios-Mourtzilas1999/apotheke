from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Τα στοιχεία σύνδεσης είναι λάθος",
        "inactive": "Ο λογαριασμός είναι ανενεργός",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Όνομα χρήστη"
        self.fields["username"].widget.attrs.update(
            {"class": "form-control login-username", "placeholder": "Enter your username", "autofocus": True}
        )
        self.fields["password"].label = "Κωδικός"
        self.fields["password"].widget.attrs.update(
            {"class": "form-control login-pwd", "placeholder": "Enter your password"}
        )


class PasswordResetForm(forms.Form):
    username = forms.CharField(label="Όνομα χρήστη", max_length=10,
                               widget=forms.TextInput(attrs={"class": "form-control forgot-username"}))
    password = forms.CharField(label="Νέος κωδικός",
                               widget=forms.PasswordInput(attrs={"class": "form-control forgot-pwd"}))
    password_confirm = forms.CharField(label="Επιβεβαίωση νέου κωδικού",
                                       widget=forms.PasswordInput(attrs={"class": "form-control forgot-pwd"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password") != cleaned.get("password_confirm"):
            raise forms.ValidationError("Οι κωδικοι δεν ταιριαζουν")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Δεν υπάρχει χρήστης με αυτό το όνομα")
        return username


class ForgotPasswordForm(forms.Form):
    username = forms.CharField(
        label="Όνομα χρήστη",
        max_length=10,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter your username"})
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError("Δεν υπάρχει χρήστης με αυτό το όνομα")
        user = User.objects.get(username=username)
        if not user.email:
            raise forms.ValidationError("Ο χρήστης δεν έχει εγγραφεί email. Παρακαλώ επικοινωνήστε με τον διαχειριστή.")
        return username


class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        label="Κωδικός OTP",
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Εισάγετε τον 6-ψήφιο κωδικό"})
    )


class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="Νέος κωδικός",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter new password"})
    )
    confirm_password = forms.CharField(
        label="Επιβεβαίωση κωδικού",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password"})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError("Οι κωδικοί δεν ταιριάζουν")

        return cleaned_data
