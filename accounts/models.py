from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
import random


class Role(models.Model):
    ADMIN, USER = "admin", "user"
    ROLE_CHOICES = [(ADMIN, "admin"), (USER, "user")]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    class Meta:
        db_table = "roles"
        constraints = [
            models.CheckConstraint(check=models.Q(role__in=["admin", "user"]), name="check_user_role")
        ]

    def __str__(self):
        return self.role


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra):
        user = self.model(username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra):
        role, _ = Role.objects.get_or_create(role=Role.ADMIN)
        return self.create_user(username, password, role=role, **extra)


class User(AbstractBaseUser):
    """Maps the Flask `users` table (username, password, role_id)."""

    # The legacy `users` table has no last_login column; drop it so the
    # existing schema matches and `migrate --fake-initial` works on it.
    last_login = None
    username = models.CharField(max_length=10, unique=True)  # varchar(10) in the legacy table
    email = models.EmailField(blank=True, null=True)
    # password (255) comes from AbstractBaseUser
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL,
                             db_column="role_id", related_name="users")

    USERNAME_FIELD = "username"
    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return bool(self.role and self.role.role == Role.ADMIN)

    # --- minimal admin-site support (no PermissionsMixin) ---
    @property
    def is_staff(self):
        return self.is_admin

    @property
    def is_superuser(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def to_dict(self):
        return {"id": self.id, "username": self.username, "role": self.role.role if self.role else None}


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_otps"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user.username}"

    @classmethod
    def generate_otp(cls, user):
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=10)
        return cls.objects.create(user=user, otp=otp_code, expires_at=expires_at)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
