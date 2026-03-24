from django.db import migrations
from decimal import Decimal
import random


def seed_products(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    SizeOption = apps.get_model("store", "SizeOption")

    db = schema_editor.connection.alias

    # Берём только подкатегории "Одежда" и "Верхняя одежда"
    target_slugs = [
        "devochki-odejda",
        "devochki-verhnya-odejda",
        "malchiki-odejda",
        "malchiki-verhnya-odejda",
        "malyshi-odejda",
        "malyshi-verhnya-odejda",
    ]
    categories = list(
        Category.objects.using(db)
        .filter(slug__in=target_slugs)
        .order_by("tree_id", "lft", "id")
    )
    if not categories:
        return

    sizes = list(SizeOption.objects.using(db).all().order_by("id"))

    brands = ["Zara", "H&M", "Next", "Adidas", "Nike", "Reserved", "C&A", "Reima", "George", "LC Waikiki"]
    seasons = ["Лето", "Зима", "Весна", "Осень", None]
    discounts = [0, 0, 0, 10, 15, 20, 25, 30, 40, 50]

    # Картинки должны существовать в MEDIA_ROOT/products/
    # media/products/seed-01.png ... media/products/seed-12.png
    seed_images = [f"products/seed-{i:02d}.png" for i in range(1, 13)]

    clothing_names = [
        "Футболка с принтом",
        "Лонгслив хлопковый",
        "Свитшот утеплённый",
        "Худи с капюшоном",
        "Джинсы прямые",
        "Брюки трикотажные",
        "Леггинсы",
        "Шорты",
        "Юбка плиссе",
        "Платье повседневное",
        "Рубашка в клетку",
        "Кофта на молнии",
        "Пижама",
        "Комплект (футболка + шорты)",
        "Спортивный костюм",
        "Комбинезон хлопковый",
    ]

    outerwear_names = [
        "Куртка демисезонная",
        "Пуховик",
        "Парка",
        "Ветровка",
        "Жилет утеплённый",
        "Пальто",
        "Дождевик",
        "Комбинезон зимний",
        "Куртка софтшелл",
        "Анорак",
        "Куртка утеплённая",
        "Плащ",
        "Куртка джинсовая",
        "Куртка-бомбер",
        "Куртка горнолыжная",
        "Полукомбинезон",
    ]

    # цены в рублях (у тебя default=7, но сделаем реалистичнее)
    price_choices = [Decimal("299"), Decimal("399"), Decimal("490"), Decimal("590"), Decimal("690"),
                     Decimal("790"), Decimal("890"), Decimal("990"), Decimal("1290"), Decimal("1590")]

    def pick_base_name(cat_slug: str) -> str:
        if cat_slug.endswith("verhnya-odejda"):
            return random.choice(outerwear_names)
        return random.choice(clothing_names)

    def make_product_name(base_name: str, brand: str, idx: int) -> str:
        # Пример: "Куртка демисезонная Reima №03"
        return f"{base_name} {brand} №{idx:02d}"

    for cat in categories:
        for i in range(1, 16):
            brand = random.choice(brands)
            base_name = pick_base_name(cat.slug)
            name = make_product_name(base_name, brand, i)

            # идемпотентность: по category+name
            if Product.objects.using(db).filter(category_id=cat.id, name=name).exists():
                continue

            product = Product.objects.using(db).create(
                name=name,
                brand=brand,
                category_id=cat.id,
                season=random.choice(seasons),
                price=random.choice(price_choices),
                discount=random.choice(discounts),
                is_active=True,
                image=random.choice(seed_images),
            )

            if sizes:
                k = random.randint(1, min(4, len(sizes)))
                picked = random.sample(sizes, k=k)
                product.sizes.add(*picked)


def unseed_products(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    db = schema_editor.connection.alias

    target_slugs = [
        "devochki-odejda",
        "devochki-verhnya-odejda",
        "malchiki-odejda",
        "malchiki-verhnya-odejda",
        "malyshi-odejda",
        "malyshi-verhnya-odejda",
    ]
    cat_ids = list(Category.objects.using(db).filter(slug__in=target_slugs).values_list("id", flat=True))
    if not cat_ids:
        return

    # удаляем только продукты внутри этих подкатегорий
    Product.objects.using(db).filter(category_id__in=cat_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0003_seed_categories"),
    ]

    operations = [
        migrations.RunPython(seed_products, unseed_products),
    ]