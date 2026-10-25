import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = ("accounts", "0001_initial")
NORMALIZED = ("accounts", "0002_normalize_emails")
LATEST = ("accounts", "0003_email_login_and_preferences")


@pytest.fixture
def migrate_accounts(transactional_db):
    state = {}

    def migrate_to(target):
        """Migrate the database to ``target`` and return the historical apps there."""
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        state["apps"] = executor.loader.project_state([target]).apps
        return state["apps"]

    yield migrate_to

    # Remove the rows a test created first: if they made a migration abort,
    # they would make it abort again on the way back to the latest state.
    state["apps"].get_model("accounts", "User").objects.all().delete()
    migrate_to(LATEST)


def test_migration_normalizes_existing_users(migrate_accounts):
    old_apps = migrate_accounts(BEFORE)
    old_user = old_apps.get_model("accounts", "User").objects.create(
        username="foo", email=" Foo@Example.COM "
    )

    new_apps = migrate_accounts(LATEST)

    user = new_apps.get_model("accounts", "User").objects.get(pk=old_user.pk)
    assert user.email == "foo@example.com"
    assert user.timezone == "UTC"
    assert user.week_start == 1
    assert user.updated_at is not None


def test_migration_aborts_on_empty_email(migrate_accounts):
    old_apps = migrate_accounts(BEFORE)
    old_user = old_apps.get_model("accounts", "User").objects.create(
        username="foo", email="  "
    )

    with pytest.raises(RuntimeError, match=rf"Users without email: \[{old_user.pk}\]"):
        migrate_accounts(NORMALIZED)


def test_migration_aborts_on_case_insensitive_duplicate(migrate_accounts):
    old_apps = migrate_accounts(BEFORE)
    OldUser = old_apps.get_model("accounts", "User")
    first = OldUser.objects.create(username="first", email="foo@example.com")
    second = OldUser.objects.create(username="second", email="FOO@example.com")

    with pytest.raises(RuntimeError) as excinfo:
        migrate_accounts(NORMALIZED)

    message = str(excinfo.value)
    assert f"[[{first.pk}, {second.pk}]]" in message
    assert "example.com" not in message
