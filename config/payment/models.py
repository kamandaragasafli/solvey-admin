from django.db import models

from doctors.models import Doctors
from regions.models import Region
from medicine.models import Medical

    

class Payment_doctor(models.Model):
    PAYMENT_TYPE = [
        ('Avans', 'Avans'),
        ('İnvest', 'İnvestisiya'),
        ('Geri_qaytarma', 'Geri Qaytarma'),

    ]
    area = models.ForeignKey(Region , on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctors , on_delete=models.CASCADE, related_name="odenisler")
    payment_type = models.CharField(max_length=200 , choices=PAYMENT_TYPE , default="Avans")
    pay = models.DecimalField(max_digits=10,decimal_places=2)
    date = models.DateField()
    is_closed = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.doctor.ad}-{self.payment_type}-{self.pay}"
    


    
    class Meta:
        verbose_name = "Həkimə Ödəniş"
        verbose_name_plural = "Həkimə Ödənişlər"

    



class Sale(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='sales')
    drug = models.ForeignKey(Medical, on_delete=models.CASCADE, related_name='sales')
    quantity = models.PositiveIntegerField()
    sale_date = models.DateField()

    def __str__(self):
        return f"{self.region.region_name} - {self.drug.med_name} - {self.quantity}"
    



    class Meta:
        verbose_name = "Bölgə Satış"
        verbose_name_plural = "Bölgə Satışları"


class MonthlyDoctorReport(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, blank=True, null=True)
    doctor = models.ForeignKey(Doctors, on_delete=models.CASCADE)
    report_month = models.DateField()  
    borc = models.FloatField(default=0)
    avans = models.FloatField(default=0)
    investisiya = models.FloatField(default=0)
    geriqaytarma = models.FloatField(default=0)
    hesablanan_miqdar = models.FloatField(default=0)
    hekimden_silinen = models.FloatField(default=0)
    yekun_borc = models.FloatField(default=0)
    recipe_total_drugs = models.IntegerField(default=0)
    recipe_drugs_list = models.TextField(blank=True)  

    class Meta:
        unique_together = ('doctor', 'report_month')  

    def __str__(self):
        return f"{self.doctor.ad} - {self.report_month.strftime('%Y-%m')}"



class Financial_document(models.Model):
    check_photo = models.ImageField(upload_to='check_photos/')
    check_dr = models.ForeignKey(Doctors, on_delete=models.CASCADE)
    check_region = models.ForeignKey(Region, on_delete=models.CASCADE, blank=True, null=True)
    check_date = models.DateField()

    def __str__(self):
        return f"{self.check_date}"