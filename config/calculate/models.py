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