from django.contrib import admin
from .models import (
    Location, Label, Item, Attachment, Currency, UserPreference,
    Dashboard, ImportLog, Collection, MaintenanceRecord, QRScan
)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')
    
@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'user', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'symbol', 'user')
    search_fields = ('name', 'code')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'quantity', 'user', 'created_at')
    search_fields = ('name', 'description', 'serial_number', 'manufacturer')
    list_filter = ('created_at', 'updated_at', 'purchase_date', 'important', 'insured', 'sold')
    readonly_fields = ('id',)

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'item', 'content_type', 'is_primary', 'created_at')
    list_filter = ('content_type', 'is_primary', 'created_at')
    readonly_fields = ('id', 'size')

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'items_per_page', 'display_mode', 'language')
    list_filter = ('theme', 'display_mode', 'language')

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')

@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'import_type', 'status', 'user', 'created_at', 'completed_at')
    list_filter = ('import_type', 'status', 'created_at')
    search_fields = ('file_name', 'error_message')
    readonly_fields = ('id', 'items_created', 'items_updated', 'items_failed')

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')

@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('item', 'date', 'cost', 'next_service_date', 'created_at')
    list_filter = ('date', 'next_service_date', 'created_at')
    search_fields = ('description',)

@admin.register(QRScan)
class QRScanAdmin(admin.ModelAdmin):
    list_display = ('item', 'scanned_at', 'ip_address')
    list_filter = ('scanned_at',)
    readonly_fields = ('id', 'scanned_at', 'ip_address', 'user_agent')