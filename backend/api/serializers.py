from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Location, Label, Item, Attachment, Currency, UserPreference,
    Dashboard, ImportLog, Collection, MaintenanceRecord, QRScan
)
import base64
import uuid
import os
from django.core.files.base import ContentFile

class Base64FileField(serializers.Field):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:'):
            # Base64 encoded file - decode
            format, filestr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(filestr), name=f'{uuid.uuid4()}.{ext}')
        return data

    def to_representation(self, value):
        if not value:
            return None
        return value.url

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Attachment
        fields = ['id', 'name', 'content_type', 'size', 'is_primary', 'created_at', 'item', 'file_url', 'thumbnail_url']
        read_only_fields = ['id', 'created_at', 'file_url', 'thumbnail_url']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url') and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url') and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None

class MaintenanceRecordSerializer(serializers.ModelSerializer):
    currency_details = CurrencySerializer(source='currency', read_only=True)
    
    class Meta:
        model = MaintenanceRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class ItemSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True, read_only=True)
    location_details = LocationSerializer(source='location', read_only=True)
    labels_details = LabelSerializer(source='labels', many=True, read_only=True)
    purchase_currency_details = CurrencySerializer(source='purchase_currency', read_only=True)
    sold_currency_details = CurrencySerializer(source='sold_currency', read_only=True)
    insured_currency_details = CurrencySerializer(source='insured_currency', read_only=True)
    primary_attachment = serializers.SerializerMethodField()
    maintenance_records = MaintenanceRecordSerializer(many=True, read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'qr_code_url']
    
    def get_primary_attachment(self, obj):
        request = self.context.get('request')
        primary = obj.attachments.filter(is_primary=True).first()
        if primary:
            return AttachmentSerializer(primary, context={'request': request}).data
        return None
    
    def get_qr_code_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/items/{obj.id}/qrcode/')
        return None
    
    def create(self, validated_data):
        labels_data = validated_data.pop('labels', [])
        item = Item.objects.create(**validated_data)
        
        for label in labels_data:
            item.labels.add(label)
        
        return item
    
    def update(self, instance, validated_data):
        labels_data = validated_data.pop('labels', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if labels_data is not None:
            instance.labels.clear()
            for label in labels_data:
                instance.labels.add(label)
        
        return instance

class UserPreferenceSerializer(serializers.ModelSerializer):
    default_currency_details = CurrencySerializer(source='default_currency', read_only=True)
    
    class Meta:
        model = UserPreference
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class ImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'user']

class CollectionSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Collection
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']
    
    def get_items_count(self, obj):
        return obj.items.count()

class QRScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRScan
        fields = '__all__'
        read_only_fields = ['id', 'scanned_at']