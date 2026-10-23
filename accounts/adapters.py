from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form):
        # Add any custom user save logic here
        return super().save_user(request, user, form)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Auto-link accounts with same email
        if sociallogin.user.pk:
            return
        
        # Try to find existing user by email
        if sociallogin.email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email=sociallogin.email)
                sociallogin.state['user'] = user
            except User.DoesNotExist:
                pass
