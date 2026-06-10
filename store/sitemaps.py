from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Category, Product


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # Укажите имена ваших статичных view (name в urls.py)
        return ['home', 'catalog']

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        # Если в модели реализован get_absolute_url — используем его
        if hasattr(obj, 'get_absolute_url') and callable(obj.get_absolute_url):
            return obj.get_absolute_url()
        # Иначе предполагаем, что у вас есть url name 'category_detail' принимающий slug
        return reverse('category_detail', args=[obj.slug])

