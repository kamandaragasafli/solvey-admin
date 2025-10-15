from django.db import models

class Backup(models.Model):
    ad = models.CharField(max_length=100)
    fayl = models.FileField(upload_to='backups/')
    olusturulma_tarixi = models.DateTimeField(auto_now_add=True)
    olcu = models.CharField(max_length=20, blank=True)  # yeni sahə: fayl ölçüsü

    def __str__(self):
        return self.ad
