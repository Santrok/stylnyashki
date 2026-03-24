from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    db = schema_editor.connection.alias

    def upsert(slug, **defaults):
        obj, _ = Category.objects.using(db).update_or_create(slug=slug, defaults=defaults)
        return obj

    # ---- Tree 1: Девочки (2 child nodes) ----
    girls = upsert(
        "devochki",
        title="Девочки",
        sub_title="Рост 92–170",
        type="level_1",
        parent=None,
        icon_background_class="cat-card--purple",
        icon_class="fas fa-female",
        fav_title="Стильняшки — Девочки",
        main_title="Одежда для девочек",
        # MPTT fields:
        level=0,
        lft=1,
        rght=6,
        tree_id=1,
    )
    upsert(
        "devochki-odejda",
        title="Одежда",
        type="category_2",
        parent=girls,
        fav_title="Одежда — Девочки",
        main_title="Одежда для девочек",
        level=1,
        lft=2,
        rght=3,
        tree_id=1,
    )
    upsert(
        "devochki-verhnya-odejda",
        title="Верхняя одежда",
        type="category_2",
        parent=girls,
        fav_title="Верхняя одежда — Девочки",
        main_title="Верхняя одежда для девочек",
        level=1,
        lft=4,
        rght=5,
        tree_id=1,
    )

    # ---- Tree 2: Мальчики (2 child nodes) ----
    boys = upsert(
        "malchiki",
        title="Мальчики",
        sub_title="Рост 92–170",
        type="level_1",
        parent=None,
        icon_background_class="cat-card--blue",
        icon_class="fas fa-tshirt",
        fav_title="Стильняшки — Мальчики",
        main_title="Одежда для мальчиков",
        level=0,
        lft=1,
        rght=6,
        tree_id=2,
    )
    upsert(
        "malchiki-odejda",
        title="Одежда",
        type="category_2",
        parent=boys,
        fav_title="Одежда — Мальчики",
        main_title="Одежда для мальчиков",
        level=1,
        lft=2,
        rght=3,
        tree_id=2,
    )
    upsert(
        "malchiki-verhnya-odejda",
        title="Верхняя одежда",
        type="category_2",
        parent=boys,
        fav_title="Верхняя одежда — Мальчики",
        main_title="Верхняя одежда для мальчиков",
        level=1,
        lft=4,
        rght=5,
        tree_id=2,
    )

    # ---- Tree 3: Малыши (2 child nodes) ----
    toddlers = upsert(
        "malyshi",
        title="Малыши",
        sub_title="0–2 года",
        type="level_1",
        parent=None,
        icon_background_class="cat-card--yellow",
        icon_class="fas fa-baby",
        fav_title="Стильняшки — Малыши",
        main_title="Одежда для малышей",
        level=0,
        lft=1,
        rght=6,
        tree_id=3,
    )
    upsert(
        "malyshi-odejda",
        title="Одежда",
        type="category_2",
        parent=toddlers,
        fav_title="Одежда — Малыши",
        main_title="Одежда для малышей",
        level=1,
        lft=2,
        rght=3,
        tree_id=3,
    )
    upsert(
        "malyshi-verhnya-odejda",
        title="Верхняя одежда",
        type="category_2",
        parent=toddlers,
        fav_title="Верхняя одежда — Малыши",
        main_title="Верхняя одежда для малышей",
        level=1,
        lft=4,
        rght=5,
        tree_id=3,
    )

    # ---- Tree 4: Скидки (no children) ----
    upsert(
        "skidky",
        sub_title="Выгода до 80%",
        title="Скидки %",
        type="level_1",
        parent=None,
        icon_background_class="cat-card--red",
        icon_class="fas fa-percent",
        fav_title="Стильняшки — Скидки",
        main_title="Скидки и акции",
        level=0,
        lft=1,
        rght=2,
        tree_id=4,
    )


def unseed_categories(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    db = schema_editor.connection.alias

    slugs = [
        "devochki", "malchiki", "malyshi", "skidky",
        "devochki-odejda", "devochki-verhnya-odejda",
        "malchiki-odejda", "malchiki-verhnya-odejda",
        "malyshi-odejda", "malyshi-verhnya-odejda",
    ]
    Category.objects.using(db).filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0002_alter_product_brand_alter_product_discount_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]