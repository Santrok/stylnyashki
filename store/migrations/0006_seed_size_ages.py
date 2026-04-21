from django.db import migrations


SIZES = [
    ("50-74", "0-9 мес"),
    ("80-92", "1-2 года"),
    ("98-104", "3-4 года"),
    ("110-116", "5-6 лет "),
    ("122-128", "7-8 лет"),
    ("134-140", "8-9 лет"),
    ("146-152", "10-12 лет"),
    ("152-164", "12-14 лет"),
]


def forwards(apps, schema_editor):
    SizeOption = apps.get_model("store", "SizeOption")
    db = schema_editor.connection.alias

    for index, value in enumerate(SIZES):
        sort = int(index)  # для роста всегда число

        SizeOption.objects.using(db).update_or_create(
            value=value[0],
            defaults={
                "age_label": value[1],
                "sort": sort,
            },
        )


def backwards(apps, schema_editor):
    SizeOption = apps.get_model("store", "SizeOption")
    db = schema_editor.connection.alias
    SizeOption.objects.using(db).filter(value__in=[v for v, _ in SIZES]).delete()


class Migration(migrations.Migration):
    dependencies = [

        ("store", "0005_alter_sizeoption_options_sizeoption_age_label_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]