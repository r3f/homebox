from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Currency, UserPreference, Dashboard
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Initialize default data for new and existing users'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        self.stdout.write(f"Found {users.count()} users")
        
        for user in users:
            self.stdout.write(f"Processing user: {user.username}")
            
            # 创建默认货币
            currencies_created = 0
            for currency_data in settings.DEFAULT_CURRENCIES:
                if not Currency.objects.filter(user=user, code=currency_data['code']).exists():
                    Currency.objects.create(
                        user=user,
                        name=currency_data['name'],
                        code=currency_data['code'],
                        symbol=currency_data['symbol']
                    )
                    currencies_created += 1
            self.stdout.write(f"  Created {currencies_created} currencies")
            
            # 创建用户首选项
            created = False
            try:
                preferences = UserPreference.objects.get(user=user)
                self.stdout.write("  User preferences already exist")
            except UserPreference.DoesNotExist:
                # 获取默认货币
                default_currency = Currency.objects.filter(user=user).first()
                
                preferences = UserPreference.objects.create(
                    user=user,
                    default_currency=default_currency,
                    theme="light",
                    items_per_page=24,
                    display_mode="grid",
                    language="en-US"
                )
                created = True
                self.stdout.write("  Created user preferences")
            
            # 确保首选项有默认货币
            if not preferences.default_currency:
                default_currency = Currency.objects.filter(user=user).first()
                if default_currency:
                    preferences.default_currency = default_currency
                    preferences.save(update_fields=['default_currency'])
                    self.stdout.write("  Updated default currency in preferences")
            
            # 创建仪表板
            try:
                Dashboard.objects.get(user=user)
                self.stdout.write("  Dashboard already exists")
            except Dashboard.DoesNotExist:
                Dashboard.objects.create(
                    user=user,
                    layout={}
                )
                self.stdout.write("  Created dashboard")
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized default data'))