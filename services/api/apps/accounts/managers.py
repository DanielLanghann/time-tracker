from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password


def normalize_email(email):
    """Return the canonical form of an email address: stripped and lower-cased."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    """Manager for users who log in with their email address instead of a username."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        """Lower-case the whole address, not only the domain as Django does."""
        return normalize_email(email)

    def get_by_natural_key(self, email):
        """Look up a user by email, ignoring case. Used by ModelBackend.authenticate()."""
        return self.get(email=normalize_email(email))

    async def aget_by_natural_key(self, email):
        """Look up a user by email, ignoring case. Used by ModelBackend.aauthenticate()."""
        return await self.aget(email=normalize_email(email))

    def _create_user(self, email, password, **extra_fields):
        """Create and save a user with a normalised email and a hashed password.

        Args:
            email: Login email address; stored lower-cased.
            password: Raw password. ``None`` creates a user with an unusable password.
            **extra_fields: Further model fields, such as names or flags.

        Returns:
            The saved user.

        Raises:
            ValueError: If the email is empty.
        """
        email = normalize_email(email)
        if not email:
            raise ValueError("The given email must be set")
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user without admin access."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    create_user.alters_data = True

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a user with full admin access.

        Args:
            email: Login email address; stored lower-cased.
            password: Raw password.
            **extra_fields: Further model fields. ``is_staff`` and ``is_superuser``
                default to ``True`` and must not be set to anything else.

        Returns:
            The saved superuser.

        Raises:
            ValueError: If the email is empty or a flag contradicts superuser status.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    create_superuser.alters_data = True
