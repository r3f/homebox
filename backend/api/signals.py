from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Attachment, UserPreference, Dashboard, Currency
from django.conf import settings
import os
from .utils import create_thumbnail

@receiver(post_save, sender=Attachment)
def generate_thumbnail(sender, instance, created, **kwargs):
    """当附件被创建时生成缩略图"""
    if created and instance.content_type.startswith('image/') and not instance.thumbnail:
        thumbnail_path = create_thumbnail(instance)
        if thumbnail_path:
            instance.thumbnail = thumbnail_path
            instance.save(update_fields=['thumbnail'])

@receiver(post_delete, sender=Attachment)
def delete_attachment_files(sender, instance, **kwargs):
    """当附件被删除时删除关联的文件"""
    # 删除原始文件
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)
    
    # 删除缩略图
    if instance.thumbnail and os.path.isfile(instance.thumbnail.path):
        os.remove(instance.thumbnail.path)

@receiver(post_save, sender=UserPreference)
def ensure_default_currency(sender, instance, created, **kwargs):
    """确保用户偏好有默认货币"""
    if not instance.default_currency:
        # 尝试查找用户的一个货币
        currency = Currency.objects.filter(user=instance.user).first()
        if currency:
            instance.default_currency = currency
            instance.save(update_fields=['default_currency'])
        else:
            # 创建默认美元货币
            currency = Currency.objects.create(
                user=instance.user,
                name='US Dollar',
                code='USD',
                symbol='$'
            )
            instance.default_currency = currency
            instance.save(update_fields=['default_currency'])