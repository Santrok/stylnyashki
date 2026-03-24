from django.db import migrations


SIZES = [
    ("56", "1-2м"),
    ("62", "2-3м"),
    ("68", "3-6м"),
    ("74", "6-9м"),
    ("80", "9-12м"),
    ("86", "1-1.5г"),
    ("92", "1.5-2г"),
    ("98", "2-3г"),
    ("104", "3-4г"),
    ("110", "4-5г"),
    ("116", "5-6г"),
    ("122", "6-7г"),
    ("128", "7-8г"),
    ("134", "8-9г"),
    ("140", "9-10г"),
    ("146", "10-11г"),
    ("152", "11-12г"),
    ("158", "12-13г"),
    ("164", "13-14г"),
]


def forwards(apps, schema_editor):
    SizeOption = apps.get_model("store", "SizeOption")
    db = schema_editor.connection.alias

    for value, age_label in SIZES:
        sort = int(value)  # для роста всегда число

        SizeOption.objects.using(db).update_or_create(
            value=value,
            defaults={
                "age_label": age_label,
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