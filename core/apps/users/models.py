from django.db import models
from django.contrib.auth.models import AbstractUser
from core.apps.common.models import (
    TimeStampModelMixin,
    AuditModelMixin,
    SoftDeleteModelMixin,
    UserManager,
)

class User(SoftDeleteModelMixin, TimeStampModelMixin, AuditModelMixin, AbstractUser):
    role = models.CharField()

    objects = UserManager()

    class Meta:
        db_table = "auth_user"

    def __str__(self):
        return self.username
