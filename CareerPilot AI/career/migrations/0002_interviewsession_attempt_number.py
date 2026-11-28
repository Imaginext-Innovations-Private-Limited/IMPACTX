from django.db import migrations, models


def populate_attempt_numbers(apps, schema_editor):
    InterviewSession = apps.get_model("career", "InterviewSession")
    for user_id in InterviewSession.objects.values_list("user_id", flat=True).distinct():
        roles = (
            InterviewSession.objects.filter(user_id=user_id)
            .values_list("role", flat=True)
            .distinct()
        )
        for role in roles:
            sessions = InterviewSession.objects.filter(user_id=user_id, role=role).order_by("created_at", "id")
            for attempt_number, session in enumerate(sessions, start=1):
                session.attempt_number = attempt_number
                session.save(update_fields=["attempt_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("career", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="interviewsession",
            name="attempt_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.RunPython(populate_attempt_numbers, migrations.RunPython.noop),
    ]
