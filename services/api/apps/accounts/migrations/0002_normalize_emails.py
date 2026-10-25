from collections import defaultdict

from django.db import migrations


def normalize_emails(apps, schema_editor):
    """Lower-case existing emails so 0003 can make them unique and canonical.

    Aborts instead of guessing when an email is empty or when two users would
    end up with the same address. Those users must be fixed by hand first.
    The error lists user IDs only, because emails are personal data.

    Raises:
        RuntimeError: If any user has an empty email or a case-insensitive duplicate.
    """
    User = apps.get_model("accounts", "User")
    users = list(User.objects.only("id", "email").order_by("pk"))

    ids_by_email = defaultdict(list)
    empty_ids = []
    for user in users:
        user.email = (user.email or "").strip().lower()
        if user.email:
            ids_by_email[user.email].append(user.pk)
        else:
            empty_ids.append(user.pk)

    duplicate_ids = [ids for ids in ids_by_email.values() if len(ids) > 1]
    if empty_ids or duplicate_ids:
        raise RuntimeError(
            "Cannot switch to email login. "
            f"Users without email: {empty_ids}. "
            f"Users sharing an email (ignoring case): {duplicate_ids}. "
            "Fix these users and run migrate again."
        )

    User.objects.bulk_update(users, ["email"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_emails, migrations.RunPython.noop),
    ]
