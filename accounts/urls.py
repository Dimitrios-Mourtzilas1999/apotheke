from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login", views.AppLoginView.as_view(), name="login"),
    path("logout", auth_views.LogoutView.as_view(), name="logout"),  # POST only (Django >= 5)
    path("reset-password", views.reset_password, name="reset_password"),
    path("forgot-password", views.forgot_password, name="forgot_password"),
    path("verify-otp", views.verify_otp, name="verify_otp"),
    path("set-new-password", views.set_new_password, name="set_new_password"),
]
