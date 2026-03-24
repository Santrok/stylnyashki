from django.db import migrations
import random


def forwards(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    SizeOption = apps.get_model("store", "SizeOption")

    db = schema_editor.connection.alias

    sizes = list(SizeOption.objects.using(db).all())
    if not sizes:
        return

    # Берём только активные товары (можно убрать фильтр, если нужно всем)
    products = Product.objects.using(db).filter(is_active=True).all()

    for p in products:
        # если размеры уже есть — не трогаем
        if p.sizes.through.objects.using(db).filter(product_id=p.id).exists():
            continue

        k = random.randint(1, min(4, len(sizes)))
        picked = random.sample(sizes, k=k)
        p.sizes.add(*picked)


def backwards(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    SizeOption = apps.get_model("store", "SizeOption")
    db = schema_editor.connection.alias

    # аккуратно удаляем связи продукт-размер (сами SizeOption не удаляем)
    through = Product.sizes.through
    size_ids = list(SizeOption.objects.using(db).values_list("id", flat=True))
    if size_ids:
        through.objects.using(db).filter(sizeoption_id__in=size_ids).delete()


class Migration(migrations.Migration):
    dependencies = [

        ("store", "0006_seed_size_ages"),

    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]