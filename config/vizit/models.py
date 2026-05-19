import hashlib

from django.db import models

from doctors.models import Doctors
from medicine.models import Medical
from regions.models import City, Region


class Istifadeci(models.Model):
    ROL_NUMAYENDE = 'numayende'
    ROL_MENECER = 'menecer'
    ROL_REHBER = 'rehber'

    ROL_CHOICES = [
        (ROL_NUMAYENDE, 'Tibbi Nümayəndə'),
        (ROL_MENECER, 'Menecer'),
        (ROL_REHBER, 'Rəhbər'),
    ]

    login = models.CharField(max_length=100, unique=True)
    sifre = models.CharField(max_length=255)
    ad = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ROL_NUMAYENDE)
    bolge = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='bolge_id',
        related_name='vizit_istifadeciler',
    )
    aktiv = models.BooleanField(default=True)

    class Meta:
        db_table = 'istifadeciler'
        ordering = ['rol', 'ad']

    def __str__(self):
        return f'{self.ad} ({self.get_rol_display()})'

    @staticmethod
    def hash_sifre(raw_password: str) -> str:
        return hashlib.md5(raw_password.encode('utf-8')).hexdigest()

    def set_password(self, raw_password: str) -> None:
        self.sifre = self.hash_sifre(raw_password)

    @classmethod
    def authenticate(cls, login: str, raw_password: str):
        if not login or not raw_password:
            return None
        return cls.objects.filter(
            login=login,
            sifre=cls.hash_sifre(raw_password),
            aktiv=True,
        ).first()

    def session_dict(self):
        return {
            'istifadeci_id': self.pk,
            'ad': self.ad,
            'rol': self.rol,
            'bolge_id': self.bolge_id,
        }


class Vizit(models.Model):
    MUNASIBAT_CHOICES = [
        ('Xatırlatma', 'Xatırlatma'),
        ('Annotasiya', 'Annotasiya'),
        ('Münasibət', 'Münasibət'),
        ('İş planı', 'İş planı'),
        ('Propaqanda', 'Propaqanda'),
    ]

    istifadeci = models.ForeignKey(
        Istifadeci, on_delete=models.PROTECT, db_column='istifadeci_id', related_name='vizitler'
    )
    hekim = models.ForeignKey(
        Doctors, on_delete=models.PROTECT, db_column='hekim_id', related_name='vizitler'
    )
    rayon = models.ForeignKey(
        City, on_delete=models.PROTECT, db_column='rayon_id', related_name='vizitler' , blank=True, null=True
    )
    bolge = models.ForeignKey(
        Region, on_delete=models.PROTECT, db_column='bolge_id', related_name='vizitler'
    )
    munasibat = models.CharField(max_length=20, choices=MUNASIBAT_CHOICES)
    tarix = models.DateField()
    vaxt = models.TimeField()
    qeyd = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vizitler'

    def __str__(self):
        return f'Vizit #{self.pk} — {self.istifadeci.ad}'


class VizitPreparat(models.Model):
    vizit = models.ForeignKey(Vizit, on_delete=models.CASCADE, db_column='vizit_id', related_name='preparatlar')
    preparat = models.ForeignKey(
        Medical, on_delete=models.PROTECT, db_column='preparat_id', related_name='vizitler'
    )

    class Meta:
        db_table = 'vizit_preparatlar'

    def __str__(self):
        return f'{self.vizit_id} — {self.preparat.med_name}'
