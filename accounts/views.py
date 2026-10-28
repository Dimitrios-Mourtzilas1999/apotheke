from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import ForgotPasswordForm, LoginForm, OTPVerificationForm, PasswordResetForm, SetNewPasswordForm
from .models import PasswordResetOTP


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def reset_password(request):
    """Change a password.

    Flask's /reset-password was public and let *anyone* set *any* user's
    password with only a username. Now: login required; normal users can only
    change their own password, admins can change anyone's.
    """
    form = PasswordResetForm(request.POST or None, initial={"username": request.user.username})
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        if username != request.user.username and not request.user.is_admin:
            messages.error(request, "Μπορείτε να αλλάξετε μόνο τον δικό σας κωδικό")
        else:
            user = get_user_model().objects.get(username=username)
            user.set_password(form.cleaned_data["password"])
            user.save(update_fields=["password"])
            messages.success(request, "Ο κωδικός σας ενημερώθηκε")
            return redirect("login")  # own session is invalidated by the password change
    return render(request, "accounts/reset_password.html", {"form": form})


def forgot_password(request):
    """Request password reset by username - sends OTP to user's email."""
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            User = get_user_model()
            user = User.objects.get(username=username)

            # Generate OTP
            otp = PasswordResetOTP.generate_otp(user)

            # Send email with OTP
            subject = "Κωδικός επαναφοράς κωδικού πρόσβασης"
            message = f"Ο κωδικός OTP για την επαναφορά του κωδικού σας είναι: {otp.otp}\n\n" \
                      f"Αυτός ο κωδικός ισχύει για 10 λεπτά.\n" \
                      f"Αν δεν ζητήσατε αυτή την ενέργεια, αγνοήστε αυτό το μήνυμα."
            from_email = None  # Uses DEFAULT_FROM_EMAIL from settings
            recipient_list = [user.email]

            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                messages.success(request, "Ο κωδικός OTP στάλθηκε στο email σας.")
                # Store username in session for next step
                request.session["reset_username"] = username
                return redirect("verify_otp")
            except Exception as e:
                messages.error(request, "Παρουσιάστηκε σφάλμα κατά την αποστολή του email. Παρακαλώ δοκιμάστε ξανά.",
                               extra_tags="danger")
                print(f"Error sending email: {e}")  # Log the error for debugging
    else:
        form = ForgotPasswordForm()

    return render(request, "accounts/forgot_password.html", {"form": form})


def verify_otp(request):
    """Verify the OTP sent to user's email."""
    username = request.session.get("reset_username")
    if not username:
        messages.error(request, "Η συνεδρία έληξε. Παρακαλώ ξεκινήστε ξανά.")
        return redirect("forgot_password")

    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, "Ο χρήστης δεν βρέθηκε.")
        return redirect("forgot_password")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data["otp"]
            # Get the latest unused OTP for this user
            otp_obj = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp_code,
                is_used=False
            ).order_by("-created_at").first()

            if otp_obj and otp_obj.is_valid():
                # Mark OTP as used
                otp_obj.is_used = True
                otp_obj.save()
                # Store user ID in session for password reset
                request.session["reset_user_id"] = user.id
                messages.success(request, "Ο κωδικός επαληθεύτηκε.")
                return redirect("set_new_password")
            else:
                messages.error(request, "Μη έγκυρος ή ληγμένος κωδικός OTP.")
    else:
        form = OTPVerificationForm()

    return render(request, "accounts/verify_otp.html", {"form": form})


def set_new_password(request):
    """Set new password after OTP verification."""
    user_id = request.session.get("reset_user_id")
    if not user_id:
        messages.error(request, "Η συνεδρία έληξε. Παρακαλώ ξεκινήστε ξανά.")
        return redirect("forgot_password")

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Ο χρήστης δεν βρέθηκε.")
        return redirect("forgot_password")

    if request.method == "POST":
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            user.set_password(new_password)
            user.save(update_fields=["password"])

            # Clear session
            request.session.pop("reset_username", None)
            request.session.pop("reset_user_id", None)

            messages.success(request, "Ο κωδικός σας άλλαξε επιτυχώς. Παρακαλώ συνδεθείτε.")
            return redirect("login")
    else:
        form = SetNewPasswordForm()

    return render(request, "accounts/set_new_password.html", {"form": form})
