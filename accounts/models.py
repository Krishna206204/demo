from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    ROLE_CHOICES = (("ADMIN", "Admin"), ("TEACHER", "Teacher"))

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="TEACHER")

    def __str__(self):
        return f"{self.username}"
    
class ModulePermission(models.Model):
    MODULE_CHOICES = [
        ('dashboard', 'Dashboard'),
        
    ]
    role = models.CharField(max_length=20,  default="TEACHER")
    module_name = models.CharField(max_length=50, choices=MODULE_CHOICES)
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'module_name')

    def __str__(self):
        return f"{self.role.role_name} - {self.module_name}"