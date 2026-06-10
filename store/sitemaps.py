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


