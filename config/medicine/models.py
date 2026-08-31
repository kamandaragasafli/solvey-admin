from django.db import models


class MedicalQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=True)


class MedicalManager(models.Manager.from_queryset(MedicalQuerySet)):
    pass


class Medical(models.Model):
    med_name = models.CharField(max_length=250)
    med_full_name = models.CharField(max_length=250, null=True, blank=True)
    med_price = models.DecimalField(max_digits=10, decimal_places=2)
    komissiya = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.BooleanField(default=True)
    in_stock = models.BooleanField(default=True)
    position = models.IntegerField(default=0)

    objects = MedicalManager()

    def __str__(self):
        return f"{self.med_name}"
    
    class Meta:
        verbose_name = "Dərman"
        verbose_name_plural = "Dərmanlar"
        db_table = 'medicine_medical'