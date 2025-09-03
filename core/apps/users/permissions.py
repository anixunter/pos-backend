from rest_framework import permissions
from core.apps.users.models import User

class IsSuperUser(permissions.BasePermission):
    """
    Custom permission to only allow super users.
    """
    def has_permission(self, request, view):
        return(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )


class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return(
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == request.user.RoleChoices.ADMIN
        )


class IsStaff(permissions.BasePermission):
    """
    Custom permission to only allow staff users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role == request.user.RoleChoices.STAFF
        )


class CustomUserPermission(permissions.BasePermission):
    """
    Custom permission that:
    - Allows superusers to do anything
    - Allows admins to do anything
    - Allows staff to:
        * View their own details (retrieve action)
        * Update their own details (update action)
        * Access the 'self' endpoint
    - For the 'self' action, any authenticated user can access.
    """
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Superuser bypasses all permissions
        if request.user.is_superuser:
            return True
            
        # Admin can do anything
        if hasattr(request.user, 'role') and request.user.role == User.RoleChoices.ADMIN:
            return True
            
        # For the 'self' action, any authenticated user is allowed
        if view.action == 'self_detail':
            return True
        
        # For retrieve/update actions, check if it's their own data
        if view.action in ['retrieve', 'update', 'partial_update']:
            # We'll check this in the view methods
            return True
        
        # Staff cannot list or create users    
        return False