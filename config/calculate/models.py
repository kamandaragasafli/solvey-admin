from django.db import models

from medicine.models import Medical




class User(models.Model):
    ROLES = [
        ('Tibbi Nümayəndə', 'Tibbi Nümayəndə'),
        ('Menecer', 'Menecer'),
        ('Rəhbər', 'Rəhbər'),
    ]

    GROUPS = [
        ('QRUP 1', 'Qrup 1'),
        ('QRUP 2', 'Qrup 2'),
    ]
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    role = models.CharField(max_length=100, choices=ROLES, default='Rəhbər')
    group = models.CharField(max_length=100, choices=GROUPS, null=True, blank=True)


    def __str__(self):
        return self.name




    # Create your models here.
class Calculate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    med = models.ForeignKey(Medical, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.name} - {self.med.med_name}"



class Report(models.Model):
    # İstifadəçi məlumatları
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # və ya sessiyadan istifadə edirsənsə
    user_name = models.CharField(max_length=150)
    user_group = models.CharField(max_length=50, blank=True, null=True)
    user_role = models.CharField(max_length=50, blank=True, null=True)

    # Hesabat məlumatları
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # JSON formatında detallı məlumat (bütün dərmanlar + miqdarlar)
    items = models.JSONField(default=dict)   # məsələn: [{"name": "Lipomag", "price": 3.0, "qty": 5, "total": 15.0}, ...]

    # Əlavə məlumat
    note = models.TextField(blank=True, null=True)  # istifadəçi qeydi
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Hesabat"
        verbose_name_plural = "Hesabatlar"

    def __str__(self):
        return f"Hesabat #{self.id} - {self.user_name} - {self.created_at.strftime('%d.%m.%Y')}"