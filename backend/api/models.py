from django.db import models
from django.contrib.auth.models import User
import uuid
import os
from datetime import datetime

class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locations')

    def __str__(self):
        return self.name

class Label(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    color = models.CharField(max_length=7, default="#3498db")  # 默认蓝色
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='labels')

    def __str__(self):
        return self.name

class Currency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=3)  # 例如: USD, EUR, JPY
    symbol = models.CharField(max_length=5)  # 例如: $, €, ¥
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='currencies')

    def __str__(self):
        return f"{self.name} ({self.code})"

class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    important = models.BooleanField(default=False)
    
    # 购买信息
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL, related_name='purchased_items')
    purchase_date = models.DateField(null=True, blank=True)
    purchase_from = models.CharField(max_length=128, blank=True, null=True)
    
    # 制造商信息
    manufacturer = models.CharField(max_length=128, blank=True, null=True)
    model_number = models.CharField(max_length=128, blank=True, null=True)
    serial_number = models.CharField(max_length=128, blank=True, null=True)
    
    # 保修信息
    warranty_expires = models.DateField(null=True, blank=True)
    warranty_info = models.TextField(blank=True, null=True)
    
    # 售出信息
    sold = models.BooleanField(default=False)
    sold_date = models.DateField(null=True, blank=True)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sold_currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL, related_name='sold_items')
    sold_to = models.CharField(max_length=128, blank=True, null=True)
    
    # 保险信息
    insured = models.BooleanField(default=False)
    insured_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    insured_currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL, related_name='insured_items')
    insurance_details = models.TextField(blank=True, null=True)
    
    # 其他信息
    notes = models.TextField(blank=True, null=True)
    added_date = models.DateTimeField(default=datetime.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 关联
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    labels = models.ManyToManyField(Label, blank=True, related_name='items')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    
    # 自定义字段 - 允许用户添加自定义属性
    custom_fields = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

def get_attachment_path(instance, filename):
    # 文件上传路径: media/user_<id>/item_<id>/<filename>
    return f'user_{instance.item.user.id}/item_{instance.item.id}/{filename}'

class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=get_attachment_path)
    name = models.CharField(max_length=256)
    content_type = models.CharField(max_length=128)
    size = models.IntegerField()
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='attachments')
    thumbnail = models.FileField(upload_to=get_attachment_path, null=True, blank=True)

    def __str__(self):
        return self.name

class UserPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    default_currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL)
    theme = models.CharField(max_length=32, default="light")
    items_per_page = models.IntegerField(default=24)
    display_mode = models.CharField(max_length=16, default="grid", choices=[("grid", "Grid"), ("list", "List")])
    language = models.CharField(max_length=5, default="en-US")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    def __str__(self):
        return f"Preferences for {self.user.username}"

class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    layout = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard')

    def __str__(self):
        return f"Dashboard for {self.user.username}"

class ImportLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    import_type = models.CharField(max_length=50)  # CSV, JSON, etc.
    status = models.CharField(max_length=50)  # Success, Failed, In Progress
    items_created = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    items_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='import_logs')

    def __str__(self):
        return f"Import {self.file_name} ({self.status})"

# 集合功能（允许将项目分组为集合）
class Collection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    items = models.ManyToManyField(Item, related_name='collections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')

    def __str__(self):
        return self.name

# 维护记录
class MaintenanceRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='maintenance_records')
    date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(Currency, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField()
    next_service_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Maintenance for {self.item.name} on {self.date}"

# QR码识别历史
class QRScan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='qr_scans')
    scanned_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"QR Scan for {self.item.name} at {self.scanned_at}"