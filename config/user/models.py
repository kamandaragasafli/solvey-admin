from django.db import models

# Create your models here.
from regions.models import Region

# Register your models here.
from django.db import models
from django.contrib.auth.models import User

class IstifadeciProfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bolge = models.ForeignKey(Region, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username
