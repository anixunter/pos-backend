from rest_framework import permissions


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