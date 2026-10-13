from django.contrib import admin
from .models import Role, User

admin.site.register(Role)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "role")
    exclude = ("password", "last_login")
