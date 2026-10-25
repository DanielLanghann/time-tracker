import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import aauthenticate, authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import User

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def user(db):
    return User.objects.create_user("foo@example.com", PASSWORD)


# Email identity


def test_create_user_stores_normalized_email(db):
    user = User.objects.create_user(" Foo@Example.COM ", PASSWORD)

    assert user.email == "foo@example.com"


def test_save_normalizes_email_without_full_clean(db):
    user = User(email="Bar@Example.com")
    user.set_password(PASSWORD)
    user.save()

    user.refresh_from_db()
    assert user.email == "bar@example.com"


def test_create_user_rejects_case_variant_of_existing_email(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("FOO@example.com", PASSWORD)


def test_database_rejects_mixed_case_email_via_update(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(email="Foo@example.com")


def test_database_rejects_mixed_case_email_via_bulk_create(db):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(email="Foo@example.com")])


def test_user_has_no_username_field():
    field_names = {field.name for field in User._meta.get_fields()}

    assert "username" not in field_names
    assert User.USERNAME_FIELD == "email"


# Required fields and validation


@pytest.mark.parametrize("email", ["", "   ", None])
def test_create_user_rejects_empty_email(db, email):
    with pytest.raises(ValueError):
        User.objects.create_user(email, PASSWORD)


def test_database_rejects_empty_email(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(email="")


def test_full_clean_rejects_invalid_timezone(user):
    user.timezone = "Mars/Olympus"

    with pytest.raises(ValidationError) as excinfo:
        user.full_clean()

    assert "timezone" in excinfo.value.message_dict


def test_full_clean_accepts_valid_timezone(user):
    user.timezone = "Europe/Berlin"

    user.full_clean()


def test_full_clean_rejects_invalid_week_start(user):
    user.week_start = 3

    with pytest.raises(ValidationError) as excinfo:
        user.full_clean()

    assert "week_start" in excinfo.value.message_dict


def test_database_rejects_invalid_week_start(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(week_start=3)


def test_preference_defaults(user):
    assert user.timezone == "UTC"
    assert user.week_start == User.WeekStart.MONDAY


def test_get_full_name_is_empty_without_names(user):
    assert user.get_full_name() == ""


# Authentication


def test_password_is_stored_hashed(user):
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)


def test_authenticate_ignores_email_case(user):
    assert authenticate(username="Foo@EXAMPLE.com", password=PASSWORD) == user


def test_aauthenticate_ignores_email_case(user):
    authenticated = async_to_sync(aauthenticate)(
        username="Foo@EXAMPLE.com", password=PASSWORD
    )

    assert authenticated == user


def test_authenticate_rejects_wrong_password(user):
    assert authenticate(username=user.email, password="wrong") is None


def test_inactive_user_cannot_authenticate(user):
    user.is_active = False
    user.save()

    assert authenticate(username=user.email, password=PASSWORD) is None


def test_create_superuser_sets_admin_flags(db):
    admin = User.objects.create_superuser("admin@example.com", PASSWORD)

    assert admin.is_staff
    assert admin.is_superuser


@pytest.mark.parametrize("flag", ["is_staff", "is_superuser"])
def test_create_superuser_rejects_contradictory_flags(db, flag):
    with pytest.raises(ValueError):
        User.objects.create_superuser("admin@example.com", PASSWORD, **{flag: False})
