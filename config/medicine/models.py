from django.db import models




class Medical(models.Model):
    med_name = models.CharField(max_length=250)
    med_full_name = models.CharField(max_length=250, null=True, blank=True)
    med_price = models.DecimalField(max_digits=10, decimal_places=2)
    komissiya = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.BooleanField(default=True)

    


    def __str__(self):
        return f"{self.med_name}"
    
    class Meta:
        verbose_name = "Dərman"
        verbose_name_plural = "Dərmanlar"
        db_table = 'medicine_medical'