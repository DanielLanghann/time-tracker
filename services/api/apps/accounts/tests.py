import pytest
from asgiref.sync import async_to_sync
from django.contrib.admin import site
from django.contrib.auth import aauthenticate, authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

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


# Admin

ADD_URL = reverse("admin:accounts_user_add")


def change_url(user):
    """Return the admin change page URL for a user."""
    return reverse("admin:accounts_user_change", args=[user.pk])


def change_form_data(user, **overrides):
    """Return a complete admin change form submission for a user.

    Args:
        user: The user being edited; supplies the current field values.
        **overrides: Form fields to replace, such as ``email`` or ``timezone``.

    Returns:
        The POST data, with unchecked flags and empty relations left out as a
        browser would.
    """
    data = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "timezone": user.timezone,
        "week_start": user.week_start,
        "is_active": "on",
        "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
        "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
        "last_login_0": "",
        "last_login_1": "",
    }
    data.update(overrides)
    return data


def test_admin_login_ignores_email_case(client, db):
    User.objects.create_superuser("admin@example.com", PASSWORD)

    response = client.post(
        reverse("admin:login"),
        {"username": "Admin@EXAMPLE.com", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert client.get(reverse("admin:index")).status_code == 200


def test_admin_add_page_has_email_and_no_username(admin_client):
    response = admin_client.get(ADD_URL)

    fields = response.context["adminform"].form.fields
    assert response.status_code == 200
    assert "email" in fields
    assert "username" not in fields


def test_admin_change_page_has_email_and_no_username(admin_client, user):
    response = admin_client.get(change_url(user))

    fields = response.context["adminform"].form.fields
    assert response.status_code == 200
    assert "email" in fields
    assert "username" not in fields


def test_admin_add_form_stores_normalized_email(admin_client):
    response = admin_client.post(
        ADD_URL,
        {
            "email": "New@Example.com",
            "usable_password": "true",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    assert response.status_code == 302
    assert User.objects.filter(email="new@example.com").exists()


def test_admin_add_form_rejects_case_variant_of_existing_email(admin_client, user):
    response = admin_client.post(
        ADD_URL,
        {
            "email": "FOO@example.com",
            "usable_password": "true",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert "email" in response.context["adminform"].form.errors
    assert User.objects.filter(email="foo@example.com").count() == 1


def test_admin_change_form_stores_normalized_email(admin_client, user):
    response = admin_client.post(
        change_url(user), change_form_data(user, email="Changed@Example.com")
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.email == "changed@example.com"


def test_admin_change_form_rejects_invalid_timezone(admin_client, user):
    response = admin_client.post(
        change_url(user), change_form_data(user, timezone="Mars/Olympus")
    )

    assert response.status_code == 200
    assert "timezone" in response.context["adminform"].form.errors
    user.refresh_from_db()
    assert user.timezone == "UTC"


def test_admin_delete_view_is_forbidden(admin_client, user):
    response = admin_client.get(reverse("admin:accounts_user_delete", args=[user.pk]))

    assert response.status_code == 403
    assert User.objects.filter(pk=user.pk).exists()


def test_admin_offers_no_bulk_delete(rf, admin_user):
    request = rf.get("/")
    request.user = admin_user

    assert "delete_selected" not in site.get_model_admin(User).get_actions(request)
