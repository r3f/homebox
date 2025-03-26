from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    """
    自定义权限：只允许对象的所有者访问它
    """
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