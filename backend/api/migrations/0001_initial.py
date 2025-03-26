# Generated by Django 5.1.7 on 2025-03-26 16:42

import api.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('description', models.TextField(blank=True, null=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('purchase_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('purchase_date', models.DateField(blank=True, null=True)),
                ('purchase_from', models.CharField(blank=True, max_length=128, null=True)),
                ('manufacturer', models.CharField(blank=True, max_length=128, null=True)),
                ('model_number', models.CharField(blank=True, max_length=128, null=True)),
                ('serial_number', models.CharField(blank=True, max_length=128, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('warranty_expires', models.DateField(blank=True, null=True)),
                ('warranty_info', models.TextField(blank=True, null=True)),
                ('sold', models.BooleanField(default=False)),
                ('sold_date', models.DateField(blank=True, null=True)),
                ('sold_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('insured', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to=api.models.get_attachment_path)),
                ('name', models.CharField(max_length=256)),
                ('content_type', models.CharField(max_length=128)),
                ('size', models.IntegerField()),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='api.item')),
            ],
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('color', models.CharField(default='#3498db', max_length=7)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='labels', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='item',
            name='labels',
            field=models.ManyToManyField(blank=True, related_name='items', to='api.label'),
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='item',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='api.location'),
        ),
    ]
