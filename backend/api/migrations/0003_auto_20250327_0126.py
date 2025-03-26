# 在最新的迁移文件中添加
from django.db import migrations
from django.conf import settings

def create_default_currencies(apps, schema_editor):
    """创建默认货币"""
    Currency = apps.get_model('api', 'Currency')
    User = apps.get_model('auth', 'User')
    
    # 获取所有用户
    for user in User.objects.all():
        # 为每个用户创建默认货币
        for currency_data in settings.DEFAULT_CURRENCIES:
            if not Currency.objects.filter(user=user, code=currency_data['code']).exists():
                Currency.objects.create(
                    user=user,
                    name=currency_data['name'],
                    code=currency_data['code'],
                    symbol=currency_data['symbol']
                )

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_attachment_thumbnail_item_added_date_and_more'),
    ]
    
    operations = [
        migrations.RunPython(create_default_currencies),
    ]