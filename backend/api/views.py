from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.temp import NamedTemporaryFile

import os
import csv
import json
import qrcode
from PIL import Image, ImageOps
from io import BytesIO
import uuid
import datetime
import magic
import zipfile
from wsgiref.util import FileWrapper

from .models import (
    Location, Label, Item, Attachment, Currency, UserPreference,
    Dashboard, ImportLog, Collection, MaintenanceRecord, QRScan
)
from .serializers import (
    LocationSerializer, LabelSerializer, ItemSerializer, AttachmentSerializer,
    CurrencySerializer, UserPreferenceSerializer, DashboardSerializer,
    ImportLogSerializer, CollectionSerializer, MaintenanceRecordSerializer,
    QRScanSerializer, UserSerializer
)

class IsOwner(permissions.BasePermission):
    """自定义权限：只允许对象的所有者访问它"""
    def has_object_permission(self, request, view, obj):
        # 检查对象是否有user属性
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # 对于Attachment，检查其关联的item的user
        if hasattr(obj, 'item'):
            return obj.item.user == request.user
        # 对于MaintenanceRecord
        if hasattr(obj, 'item') and hasattr(obj.item, 'user'):
            return obj.item.user == request.user
        return False

class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    def get_queryset(self):
        return Location.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """获取该位置下的所有物品"""
        location = self.get_object()
        items = Item.objects.filter(location=location)
        serializer = ItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """返回位置统计数据"""
        locations = self.get_queryset()
        data = []
        
        for location in locations:
            item_count = Item.objects.filter(location=location).count()
            data.append({
                'id': str(location.id),
                'name': location.name,
                'item_count': item_count
            })
        
        return Response(data)

class LabelViewSet(viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    def get_queryset(self):
        return Label.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """获取该标签下的所有物品"""
        label = self.get_object()
        items = Item.objects.filter(labels=label)
        serializer = ItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """返回标签统计数据"""
        labels = self.get_queryset()
        data = []
        
        for label in labels:
            item_count = Item.objects.filter(labels=label).count()
            data.append({
                'id': str(label.id),
                'name': label.name,
                'color': label.color,
                'item_count': item_count
            })
        
        return Response(data)

class CurrencyViewSet(viewsets.ModelViewSet):
    serializer_class = CurrencySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'symbol']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['code']

    def get_queryset(self):
        return Currency.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def init_defaults(self, request):
        """初始化默认货币"""
        created_count = 0
        for currency_data in settings.DEFAULT_CURRENCIES:
            if not Currency.objects.filter(user=request.user, code=currency_data['code']).exists():
                Currency.objects.create(
                    user=request.user,
                    name=currency_data['name'],
                    code=currency_data['code'],
                    symbol=currency_data['symbol']
                )
                created_count += 1
        
        return Response({'message': f'Created {created_count} default currencies'})

class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['location', 'important', 'insured', 'sold']
    search_fields = ['name', 'description', 'serial_number', 'model_number', 'manufacturer', 'notes']
    ordering_fields = ['name', 'created_at', 'updated_at', 'purchase_date', 'quantity', 'purchase_price']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Item.objects.filter(user=self.request.user)
        
        # 标签过滤
        label = self.request.query_params.get('label')
        if label:
            queryset = queryset.filter(labels__id=label)
        
        # 搜索
        search = self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(model_number__icontains=search) |
                Q(manufacturer__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def qrcode(self, request, pk=None):
        """为物品生成QR码"""
        item = self.get_object()
        
        # 创建QR码
        qr = qrcode.QRCode(
            version=settings.QR_CODE_VERSION,
            error_correction=getattr(qrcode.constants, f'ERROR_CORRECT_{settings.QR_CODE_ERROR_CORRECTION}'),
            box_size=10,
            border=4,
        )
        
        # QR码数据
        qr_data = {
            'id': str(item.id),
            'name': item.name,
            'url': request.build_absolute_uri(f'/items/{item.id}')
        }
        
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 将QR码转换为HTTP响应
        response = HttpResponse(content_type="image/png")
        img.save(response, "PNG")
        
        # 记录QR码扫描
        if request.query_params.get('scan') == 'true':
            QRScan.objects.create(
                item=item,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        
        return response
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """导出CSV格式的物品列表"""
        items = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="homebox_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Description', 'Quantity', 'Important', 'Purchase Price', 
            'Purchase Currency', 'Purchase Date', 'Purchase From', 'Manufacturer', 
            'Model Number', 'Serial Number', 'Notes', 'Warranty Expires', 
            'Warranty Info', 'Sold', 'Sold Date', 'Sold Price', 'Sold Currency', 
            'Sold To', 'Insured', 'Insured Value', 'Insured Currency', 
            'Insurance Details', 'Location', 'Labels', 'Created At', 'Updated At'
        ])
        
        for item in items:
            labels = ', '.join([label.name for label in item.labels.all()])
            location_name = item.location.name if item.location else ''
            purchase_currency = item.purchase_currency.code if item.purchase_currency else ''
            sold_currency = item.sold_currency.code if item.sold_currency else ''
            insured_currency = item.insured_currency.code if item.insured_currency else ''
            
            writer.writerow([
                item.name, item.description, item.quantity, item.important,
                item.purchase_price, purchase_currency, item.purchase_date, 
                item.purchase_from, item.manufacturer, item.model_number,
                item.serial_number, item.notes, item.warranty_expires, 
                item.warranty_info, item.sold, item.sold_date, item.sold_price, 
                sold_currency, item.sold_to, item.insured, item.insured_value, 
                insured_currency, item.insurance_details, location_name, labels,
                item.created_at, item.updated_at
            ])
        
        # 记录导出
        ImportLog.objects.create(
            user=request.user,
            file_name=f"homebox_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv",
            file_size=len(response.content),
            import_type='CSV Export',
            status='Success',
            items_created=0,
            items_updated=0,
            items_failed=0,
            completed_at=timezone.now()
        )
        
        return response
    
    @action(detail=False, methods=['get'])
    def export_json(self, request):
        """导出JSON格式的物品列表"""
        items = self.get_queryset()
        data = []
        
        for item in items:
            labels = [{"id": str(label.id), "name": label.name, "color": label.color} 
                    for label in item.labels.all()]
            location = {"id": str(item.location.id), "name": item.location.name} if item.location else None
            purchase_currency = {"id": str(item.purchase_currency.id), "code": item.purchase_currency.code, "symbol": item.purchase_currency.symbol} if item.purchase_currency else None
            sold_currency = {"id": str(item.sold_currency.id), "code": item.sold_currency.code, "symbol": item.sold_currency.symbol} if item.sold_currency else None
            insured_currency = {"id": str(item.insured_currency.id), "code": item.insured_currency.code, "symbol": item.insured_currency.symbol} if item.insured_currency else None
            
            attachments = []
            for att in item.attachments.all():
                attachments.append({
                    "id": str(att.id),
                    "name": att.name,
                    "content_type": att.content_type,
                    "size": att.size,
                    "is_primary": att.is_primary,
                    "created_at": att.created_at.isoformat(),
                    "file_url": request.build_absolute_uri(att.file.url) if att.file else None,
                    "thumbnail_url": request.build_absolute_uri(att.thumbnail.url) if att.thumbnail else None
                })
            
            maintenance_records = []
            for record in item.maintenance_records.all():
                maintenance_records.append({
                    "id": str(record.id),
                    "date": record.date.isoformat() if record.date else None,
                    "cost": float(record.cost) if record.cost else None,
                    "currency": {"id": str(record.currency.id), "code": record.currency.code} if record.currency else None,
                    "description": record.description,
                    "next_service_date": record.next_service_date.isoformat() if record.next_service_date else None,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat()
                })
            
            item_data = {
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "quantity": item.quantity,
                "important": item.important,
                "purchase_price": float(item.purchase_price) if item.purchase_price else None,
                "purchase_currency": purchase_currency,
                "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
                "purchase_from": item.purchase_from,
                "manufacturer": item.manufacturer,
                "model_number": item.model_number,
                "serial_number": item.serial_number,
                "notes": item.notes,
                "warranty_expires": item.warranty_expires.isoformat() if item.warranty_expires else None,
                "warranty_info": item.warranty_info,
                "sold": item.sold,
                "sold_date": item.sold_date.isoformat() if item.sold_date else None,
                "sold_price": float(item.sold_price) if item.sold_price else None,
                "sold_currency": sold_currency,
                "sold_to": item.sold_to,
                "insured": item.insured,
                "insured_value": float(item.insured_value) if item.insured_value else None,
                "insured_currency": insured_currency,
                "insurance_details": item.insurance_details,
                "location": location,
                "labels": labels,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "custom_fields": item.custom_fields,
                "attachments": attachments,
                "maintenance_records": maintenance_records
            }
            data.append(item_data)
        
        response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="homebox_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        # 记录导出
        ImportLog.objects.create(
            user=request.user,
            file_name=f"homebox_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json",
            file_size=len(response.content),
            import_type='JSON Export',
            status='Success',
            items_created=0,
            items_updated=0,
            items_failed=0,
            completed_at=timezone.now()
        )
        
        return response
    
    @action(detail=False, methods=['post'])
    def import_json(self, request):
        """从JSON导入物品"""
        try:
            if 'file' in request.FILES:
                json_file = request.FILES['file']
                json_data = json.loads(json_file.read().decode('utf-8'))
            else:
                json_data = request.data
            
            if not json_data:
                return Response({"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            log = ImportLog.objects.create(
                user=request.user,
                file_name=getattr(request.FILES.get('file'), 'name', 'Direct JSON import'),
                file_size=getattr(request.FILES.get('file'), 'size', 0),
                import_type='JSON Import',
                status='In Progress'
            )
            
            items_created = 0
            items_updated = 0
            items_failed = 0
            error_messages = []
            
            for item_data in json_data:
                try:
                    # 处理位置
                    location_data = item_data.pop('location', None)
                    location = None
                    if location_data and 'name' in location_data:
                        location, _ = Location.objects.get_or_create(
                            user=request.user,
                            name=location_data['name'],
                            defaults={'description': ''}
                        )
                    
                    # 处理标签
                    labels_data = item_data.pop('labels', [])
                    labels = []
                    for label_data in labels_data:
                        if 'name' in label_data:
                            label, _ = Label.objects.get_or_create(
                                user=request.user,
                                name=label_data['name'],
                                defaults={'color': label_data.get('color', '#3498db')}
                            )
                            labels.append(label)
                    
                    # 处理货币
                    purchase_currency_data = item_data.pop('purchase_currency', None)
                    purchase_currency = None
                    if purchase_currency_data and 'code' in purchase_currency_data:
                        purchase_currency, _ = Currency.objects.get_or_create(
                            user=request.user,
                            code=purchase_currency_data['code'],
                            defaults={
                                'name': purchase_currency_data.get('name', purchase_currency_data['code']),
                                'symbol': purchase_currency_data.get('symbol', '')
                            }
                        )
                    
                    sold_currency_data = item_data.pop('sold_currency', None)
                    sold_currency = None
                    if sold_currency_data and 'code' in sold_currency_data:
                        sold_currency, _ = Currency.objects.get_or_create(
                            user=request.user,
                            code=sold_currency_data['code'],
                            defaults={
                                'name': sold_currency_data.get('name', sold_currency_data['code']),
                                'symbol': sold_currency_data.get('symbol', '')
                            }
                        )
                    
                    insured_currency_data = item_data.pop('insured_currency', None)
                    insured_currency = None
                    if insured_currency_data and 'code' in insured_currency_data:
                        insured_currency, _ = Currency.objects.get_or_create(
                            user=request.user,
                            code=insured_currency_data['code'],
                            defaults={
                                'name': insured_currency_data.get('name', insured_currency_data['code']),
                                'symbol': insured_currency_data.get('symbol', '')
                            }
                        )
                    
                    # 移除不需要的字段
                    item_id = item_data.pop('id', None)
                    item_data.pop('attachments', None)
                    item_data.pop('maintenance_records', None)
                    item_data.pop('created_at', None)
                    item_data.pop('updated_at', None)
                    
                    # 处理日期字段
                    for date_field in ['purchase_date', 'warranty_expires', 'sold_date']:
                        if date_field in item_data and item_data[date_field]:
                            try:
                                item_data[date_field] = datetime.datetime.fromisoformat(item_data[date_field]).date()
                            except ValueError:
                                item_data[date_field] = None
                    
                    # 查找或创建物品
                    item = None
                    if item_id:
                        try:
                            item = Item.objects.get(id=item_id, user=request.user)
                            items_updated += 1
                        except Item.DoesNotExist:
                            pass
                    
                    if not item:
                        item = Item(user=request.user)
                        items_created += 1
                    
                    # 设置物品字段
                    for key, value in item_data.items():
                        setattr(item, key, value)
                    
                    item.location = location
                    item.purchase_currency = purchase_currency
                    item.sold_currency = sold_currency
                    item.insured_currency = insured_currency
                    item.save()
                    
                    # 添加标签
                    item.labels.clear()
                    for label in labels:
                        item.labels.add(label)
                    
                except Exception as e:
                    items_failed += 1
                    error_messages.append(str(e))
            
            # 更新导入日志
            log.status = 'Success' if items_failed == 0 else 'Partial Success' if items_created + items_updated > 0 else 'Failed'
            log.items_created = items_created
            log.items_updated = items_updated
            log.items_failed = items_failed
            log.error_message = '\n'.join(error_messages[:10]) + (f'\n...and {len(error_messages)-10} more errors' if len(error_messages) > 10 else '')
            log.completed_at = timezone.now()
            log.save()
            
            return Response({
                "success": f"Imported {items_created + items_updated} items ({items_created} created, {items_updated} updated)",
                "failed": items_failed,
                "errors": error_messages[:10] if error_messages else None
            }, status=status.HTTP_201_CREATED if items_failed == 0 else status.HTTP_207_MULTI_STATUS)
        
        except Exception as e:
            # 记录导入失败
            ImportLog.objects.create(
                user=request.user,
                file_name=getattr(request.FILES.get('file'), 'name', 'Direct JSON import'),
                file_size=getattr(request.FILES.get('file'), 'size', 0),
                import_type='JSON Import',
                status='Failed',
                error_message=str(e),
                completed_at=timezone.now()
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        """从CSV导入物品"""
        try:
            if 'file' not in request.FILES:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            csv_file = request.FILES['file']
            
            log = ImportLog.objects.create(
                user=request.user,
                file_name=csv_file.name,
                file_size=csv_file.size,
                import_type='CSV Import',
                status='In Progress'
            )
            
            # 解析CSV文件
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            items_created = 0
            items_updated = 0
            items_failed = 0
            error_messages = []
            
            for row in reader:
                try:
                    # 处理位置
                    location_name = row.get('Location', '').strip()
                    location = None
                    if location_name:
                        location, _ = Location.objects.get_or_create(
                            user=request.user,
                            name=location_name,
                            defaults={'description': ''}
                        )
                    
                    # 处理标签
                    labels_names = [name.strip() for name in row.get('Labels', '').split(',') if name.strip()]
                    labels = []
                    for label_name in labels_names:
                        label, _ = Label.objects.get_or_create(
                            user=request.user,
                            name=label_name,
                            defaults={'color': '#3498db'}
                        )
                        labels.append(label)
                    
                    # 创建物品
                    item = Item(user=request.user)
                    
                    # 设置字段
                    item.name = row.get('Name', '').strip()
                    item.description = row.get('Description', '').strip()
                    item.quantity = int(row.get('Quantity', 1)) if row.get('Quantity', '').strip() else 1
                    item.important = row.get('Important', '').lower() in ('yes', 'true', '1')
                    
                    # 价格和购买信息
                    purchase_price = row.get('Purchase Price', '').strip()
                    if purchase_price:
                        try:
                            item.purchase_price = float(purchase_price)
                        except ValueError:
                            pass
                    
                    purchase_currency_code = row.get('Purchase Currency', '').strip()
                    if purchase_currency_code:
                        currency, _ = Currency.objects.get_or_create(
                            user=request.user,
                            code=purchase_currency_code,
                            defaults={'name': purchase_currency_code, 'symbol': ''}
                        )
                        item.purchase_currency = currency
                    
                    purchase_date = row.get('Purchase Date', '').strip()
                    if purchase_date:
                        try:
                            item.purchase_date = datetime.datetime.strptime(purchase_date, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                item.purchase_date = datetime.datetime.strptime(purchase_date, '%m/%d/%Y').date()
                            except ValueError:
                                pass
                    
                    item.purchase_from = row.get('Purchase From', '').strip()
                    item.manufacturer = row.get('Manufacturer', '').strip()
                    item.model_number = row.get('Model Number', '').strip()
                    item.serial_number = row.get('Serial Number', '').strip()
                    item.notes = row.get('Notes', '').strip()
                    
                    # 保修信息
                    warranty_expires = row.get('Warranty Expires', '').strip()
                    if warranty_expires:
                        try:
                            item.warranty_expires = datetime.datetime.strptime(warranty_expires, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                item.warranty_expires = datetime.datetime.strptime(warranty_expires, '%m/%d/%Y').date()
                            except ValueError:
                                pass
                    
                    item.warranty_info = row.get('Warranty Info', '').strip()
                    
                    # 售出信息
                    item.sold = row.get('Sold', '').lower() in ('yes', 'true', '1')
                    
                    sold_date = row.get('Sold Date', '').strip()
                    if sold_date:
                        try:
                            item.sold_date = datetime.datetime.strptime(sold_date, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                item.sold_date = datetime.datetime.strptime(sold_date, '%m/%d/%Y').date()
                            except ValueError:
                                pass
                    
                    sold_price = row.get('Sold Price', '').strip()
                    if sold_price:
                        try:
                            item.sold_price = float(sold_price)
                        except ValueError:
                            pass
                    
                    sold_currency_code = row.get('Sold Currency', '').strip()
                    if sold_currency_code:
                        currency, _ = Currency.objects.get_or_create(
                            user=request.user,
                            code=sold_currency_code,
                            defaults={'name': sold_currency_code, 'symbol': ''}
                        )
                        item.sold_currency = currency
                    
                    item.sold_to = row.get('Sold To', '').strip()
                    
                    # 保险信息
                    item.insured = row.get('Insured', '').lower() in ('yes', 'true', '1')
                    
                    insured_value = row.get('Insured Value', '').strip()
                    if insured_value:
                        try:
                            item.insured_value = float(insured_value)
                        except ValueError:
                            pass
                    
                    insured_currency_code = row.get('Insured Currency', '').strip()
                    if insured_currency_code:
                        currency, _ = Currency.objects.get_or_create(
                            user=request.user,
                            code=insured_currency_code,
                            defaults={'name': insured_currency_code, 'symbol': ''}
                        )
                        item.insured_currency = currency
                    
                    item.insurance_details = row.get('Insurance Details', '').strip()
                    
                    # 关联位置和保存
                    item.location = location
                    item.save()
                    
                    # 添加标签
                    for label in labels:
                        item.labels.add(label)
                    
                    items_created += 1
                    
                except Exception as e:
                    items_failed += 1
                    error_messages.append(f"Error importing row {items_created + items_failed}: {str(e)}")
            
            # 更新导入日志
            log.status = 'Success' if items_failed == 0 else 'Partial Success' if items_created > 0 else 'Failed'
            log.items_created = items_created
            log.items_updated = items_updated
            log.items_failed = items_failed
            log.error_message = '\n'.join(error_messages[:10]) + (f'\n...and {len(error_messages)-10} more errors' if len(error_messages) > 10 else '')
            log.completed_at = timezone.now()
            log.save()
            
            return Response({
                "success": f"Imported {items_created} items",
                "failed": items_failed,
                "errors": error_messages[:10] if error_messages else None
            }, status=status.HTTP_201_CREATED if items_failed == 0 else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            # 记录导入失败
            ImportLog.objects.create(
                user=request.user,
                file_name=csv_file.name if 'csv_file' in locals() else 'Unknown CSV',
                file_size=csv_file.size if 'csv_file' in locals() else 0,
                import_type='CSV Import',
                status='Failed',
                error_message=str(e),
                completed_at=timezone.now()
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取物品统计数据"""
        queryset = self.get_queryset()
        
        total_items = queryset.count()
        total_value = queryset.exclude(purchase_price=None).aggregate(Sum('purchase_price'))['purchase_price__sum'] or 0
        insured_items = queryset.filter(insured=True).count()
        insured_value = queryset.filter(insured=True).exclude(insured_value=None).aggregate(Sum('insured_value'))['insured_value__sum'] or 0
        sold_items = queryset.filter(sold=True).count()
        important_items = queryset.filter(important=True).count()
        
        # 按位置分组
        locations = Location.objects.filter(user=request.user)
        location_stats = []
        for location in locations:
            location_items = queryset.filter(location=location).count()
            if location_items > 0:
                location_stats.append({
                    'id': str(location.id),
                    'name': location.name,
                    'count': location_items
                })
        
        # 按标签分组
        labels = Label.objects.filter(user=request.user)
        label_stats = []
        for label in labels:
            label_items = queryset.filter(labels=label).count()
            if label_items > 0:
                label_stats.append({
                    'id': str(label.id),
                    'name': label.name,
                    'color': label.color,
                    'count': label_items
                })
        
        return Response({
            'total_items': total_items,
            'total_value': total_value,
            'insured_items': insured_items,
            'insured_value': insured_value,
            'sold_items': sold_items,
            'important_items': important_items,
            'locations': location_stats,
            'labels': label_stats
        })
    
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """查找相似物品"""
        item = self.get_object()
        queryset = Item.objects.filter(user=request.user).exclude(id=item.id)
        
        # 基于名称、制造商和标签查找相似项
        similar_items = []
        
        # 基于名称相似度
        if item.name:
            name_parts = item.name.lower().split()
            for part in name_parts:
                if len(part) > 3:  # 忽略短词
                    name_matches = queryset.filter(name__icontains=part)
                    similar_items.extend(list(name_matches))
        
        # 基于制造商
        if item.manufacturer:
            manufacturer_matches = queryset.filter(manufacturer__iexact=item.manufacturer)
            similar_items.extend(list(manufacturer_matches))
        
        # 基于标签
        labels = item.labels.all()
        if labels:
            label_matches = queryset.filter(labels__in=labels).distinct()
            similar_items.extend(list(label_matches))
        
        # 去重并限制结果数量
        similar_items = list(set(similar_items))[:12]
        
        serializer = self.get_serializer(similar_items, many=True)
        return Response(serializer.data)

class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Attachment.objects.filter(item__user=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        item_id = request.data.get('item')
        if not item_id:
            return Response({"error": "Item ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        item = get_object_or_404(Item, id=item_id, user=request.user)
        
        files = request.FILES.getlist('file')
        if not files:
            return Response({"error": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        attachments = []
        for file in files:
            # 检测是否为主图片
            is_primary = request.data.get('is_primary', 'false').lower() == 'true'
            
            # 如果这是一个主图片，将其他图片设为非主图片
            if is_primary:
                Attachment.objects.filter(item=item, is_primary=True).update(is_primary=False)
            
            # 创建附件
            attachment = Attachment(
                item=item,
                file=file,
                name=file.name,
                content_type=file.content_type or magic.from_buffer(file.read(1024), mime=True),
                size=file.size,
                is_primary=is_primary
            )
            attachment.save()
            
            # 如果是图片，生成缩略图
            if attachment.content_type.startswith('image/'):
                try:
                    img = Image.open(attachment.file.path)
                    img.thumbnail(settings.THUMBNAIL_SIZE)
                    
                    # 创建缩略图文件名
                    thumbnail_name = f"thumb_{os.path.basename(attachment.file.name)}"
                    thumbnail_path = os.path.join(os.path.dirname(attachment.file.path), thumbnail_name)
                    
                    img.save(thumbnail_path, quality=settings.THUMBNAIL_QUALITY)
                    
                    # 设置缩略图路径
                    relative_path = os.path.join(os.path.dirname(attachment.file.name), thumbnail_name)
                    attachment.thumbnail.name = relative_path
                    attachment.save()
                except Exception as e:
                    # 缩略图生成失败不影响上传
                    print(f"Thumbnail generation failed: {e}")
            
            attachments.append(attachment)
        
        serializer = self.get_serializer(attachments[0] if len(attachments) == 1 else attachments, many=len(attachments) > 1)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def set_as_primary(self, request, pk=None):
        """设置附件为主要附件"""
        attachment = self.get_object()
        
        # 将同一物品的其他附件设为非主要
        Attachment.objects.filter(item=attachment.item, is_primary=True).update(is_primary=False)
        
        # 将此附件设为主要
        attachment.is_primary = True
        attachment.save()
        
        serializer = self.get_serializer(attachment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """下载附件"""
        attachment = self.get_object()
        
        if not os.path.exists(attachment.file.path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        
        response = FileWrapper(open(attachment.file.path, 'rb'))
        content_type = attachment.content_type or 'application/octet-stream'
        response = HttpResponse(response, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{attachment.name}"'
        response['Content-Length'] = attachment.size
        
        return response

class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return MaintenanceRecord.objects.filter(item__user=self.request.user)
    
    def perform_create(self, serializer):
        item_id = self.request.data.get('item')
        item = get_object_or_404(Item, id=item_id, user=self.request.user)
        serializer.save(item=item)

class UserPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        # 获取或创建用户首选项
        preferences, created = UserPreference.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        # 转为更新操作
        preferences, created = UserPreference.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(preferences, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)

class DashboardViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dashboard.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        # 获取或创建用户仪表板
        dashboard, created = Dashboard.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(dashboard)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        # 转为更新操作
        dashboard, created = Dashboard.objects.get_or_create(user=request.user)
        
        serializer = self.get_serializer(dashboard, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)

class ImportLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ImportLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'completed_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return ImportLog.objects.filter(user=self.request.user)

class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return Collection.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_items(self, request, pk=None):
        """向集合添加物品"""
        collection = self.get_object()
        item_ids = request.data.get('items', [])
        
        added = 0
        for item_id in item_ids:
            try:
                item = Item.objects.get(id=item_id, user=request.user)
                collection.items.add(item)
                added += 1
            except Item.DoesNotExist:
                pass
        
        return Response({'success': f'Added {added} items to collection'})
    
    @action(detail=True, methods=['post'])
    def remove_items(self, request, pk=None):
        """从集合移除物品"""
        collection = self.get_object()
        item_ids = request.data.get('items', [])
        
        removed = 0
        for item_id in item_ids:
            try:
                item = Item.objects.get(id=item_id, user=request.user)
                collection.items.remove(item)
                removed += 1
            except Item.DoesNotExist:
                pass
        
        return Response({'success': f'Removed {removed} items from collection'})
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """获取集合中的所有物品"""
        collection = self.get_object()
        items = collection.items.all()
        
        serializer = ItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

class QRScanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QRScanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['scanned_at']
    ordering = ['-scanned_at']

    def get_queryset(self):
        return QRScan.objects.filter(item__user=self.request.user)