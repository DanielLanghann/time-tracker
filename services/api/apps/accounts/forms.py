from django.contrib.auth import forms as auth_forms

from .models import User


class UserCreationForm(auth_forms.AdminUserCreationForm):
    class Meta(auth_forms.AdminUserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeForm(auth_forms.UserChangeForm):
    class Meta(auth_forms.UserChangeForm.Meta):
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "timezone",
            "week_start",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
        )
