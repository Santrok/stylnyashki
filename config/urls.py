"""Root URL configuration."""

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page

from store.sitemaps import StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap(),
}

urlpatterns = [
      path('admin/', admin.site.urls),
      path('', include('store.urls')),
      path('sitemap.xml', cache_page(60 * 60)(sitemap), {'sitemaps': sitemaps}, name='sitemap'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
