import os

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Profile, Product

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(pre_delete, sender=Product)
def product_image_delete(sender, instance, **kwargs):
    """
    Удаление файлов и папок, перед удалением экземпляра товара.
    """
    image_folder = os.path.dirname(instance.image.path) if instance.image else None
    instance.image.delete(False)
    if image_folder and os.path.exists(image_folder) and os.path.isdir(image_folder):
        if not os.listdir(image_folder):
            os.rmdir(image_folder)