from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager

class TimeStampModelMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        abstract = True


class AuditModelMixin(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated",
        editable=False,
    )

    class Meta:
        abstract = True
        

class SoftDeleteQuerySet(models.QuerySet):
    """
    Custom QuerySet for soft delete functionality.
    """

    def delete(self, user=None):
        return super().update(
            is_deleted=True, deleted_at=timezone.now(), deleted_by=user
        )

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """
    Manager that returns only non-deleted instances by default.
    """

    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop("alive_only", True)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.alive_only:
            return SoftDeleteQuerySet(self.model).filter(is_deleted=False)
        return SoftDeleteQuerySet(self.model)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class SoftDeleteModelMixin(models.Model):
    """
    Mixin to add soft delete functionality with audit trail.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_deleted",
        editable=False,
    )

    # default manager returns only non-deleted objects
    objects = SoftDeleteManager()
    # manager that returns all objects including deleted ones
    all_objects = SoftDeleteManager(alive_only=False)

    class Meta:
        abstract = True

    def delete(self, user=None):
        """
        Soft delete: mark as deleted
        """
        if self.is_deleted:
            return

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        # save only the fields related to soft delete
        update_fields = ["is_deleted", "deleted_at", "deleted_by"]
        self.save(update_fields=update_fields)

    def restore(self, user=None):
        """
        Restore a soft-deleted object
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = user
        self.save()

    def hard_delete(self, *args, **kwargs):
        """
        Hard delete from database
        """
        super().delete(*args, **kwargs)


class UserManager(BaseUserManager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model).filter(is_deleted=False)

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        if not username:
            raise ValueError("The Username must be set")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self.db)

        return user

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(username, email, password, **extra_fields)
