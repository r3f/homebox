from PIL import Image, ImageOps
import os
import qrcode
import io
import json
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
import csv
from datetime import datetime

def create_thumbnail(attachment):
    """为附件创建缩略图"""
    if not attachment.file or not attachment.content_type.startswith('image/'):
        return None
    
    try:
        img = Image.open(attachment.file.path)
        
        # 调整图片大小
        img.thumbnail(settings.THUMBNAIL_SIZE)
        
        # 创建缩略图文件名
        thumbnail_name = f"thumb_{os.path.basename(attachment.file.name)}"
        thumbnail_path = os.path.join(os.path.dirname(attachment.file.path), thumbnail_name)
        
        # 保存缩略图
        img.save(thumbnail_path, quality=settings.THUMBNAIL_QUALITY)
        
        # 返回相对路径
        relative_path = os.path.join(os.path.dirname(attachment.file.name), thumbnail_name)
        return relative_path
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None

def generate_qrcode(item, base_url):
    """为物品生成QR码"""
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
        'url': f"{base_url}/items/{item.id}"
    }
    
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 转换为字节流
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

def export_items_to_csv(items, user):
    """导出物品到CSV文件"""
    output = io.StringIO()
    writer = csv.writer(output)
    
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
            item.name, item.description, item.quantity, 'Yes' if item.important else 'No',
            item.purchase_price, purchase_currency, item.purchase_date, 
            item.purchase_from, item.manufacturer, item.model_number,
            item.serial_number, item.notes, item.warranty_expires, 
            item.warranty_info, 'Yes' if item.sold else 'No', item.sold_date, item.sold_price, 
            sold_currency, item.sold_to, 'Yes' if item.insured else 'No', item.insured_value, 
            insured_currency, item.insurance_details, location_name, labels,
            item.created_at, item.updated_at
        ])
    
    return output.getvalue()

def export_items_to_json(items, request):
    """导出物品为JSON格式"""
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
    
    return json.dumps(data, indent=2)