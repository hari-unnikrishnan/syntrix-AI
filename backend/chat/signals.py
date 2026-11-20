from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import UploadedDocument


@receiver(pre_delete, sender=UploadedDocument)
def remove_private_document_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
