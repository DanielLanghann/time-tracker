from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from .managers import UserManager, normalize_email
from .validators import validate_timezone


class User(AbstractUser):
    """A person who logs in with their email address.

    Holds only workspace-independent data. Roles and hourly rates live on
    workspace and stream memberships.
    """

    class WeekStart(models.IntegerChoices):
        MONDAY = 1, "Monday"
        SUNDAY = 7, "Sunday"

    username = None
    email = models.EmailField("email address", unique=True)

    timezone = models.CharField(
        max_length=64, default="UTC", validators=[validate_timezone]
    )
    week_start = models.PositiveSmallIntegerField(
        choices=WeekStart, default=WeekStart.MONDAY
    )
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    # Annotated so type checkers use this manager instead of the username-based
    # UserManager that the Django stubs declare on AbstractUser.
    objects: ClassVar[UserManager] = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = (
            # Stored emails are canonical (lower-case, no whitespace), so the
            # plain unique index on email also catches variants of an address,
            # even for writes that skip save().
            models.CheckConstraint(
                condition=Q(email=Lower("email")),
                name="accounts_user_email_lowercase",
            ),
            models.CheckConstraint(
                condition=~Q(email__regex=r"\s"),
                name="accounts_user_email_no_whitespace",
            ),
            models.CheckConstraint(
                condition=~Q(email=""),
                name="accounts_user_email_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(week_start__in=[1, 7]),
                name="accounts_user_week_start_valid",
            ),
        )

    def save(self, **kwargs):
        """Store the email in canonical form, also when full_clean() was skipped."""
        self.email = normalize_email(self.email)
        super().save(**kwargs)
