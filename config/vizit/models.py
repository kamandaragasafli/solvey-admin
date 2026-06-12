import hashlib

from django.db import models

from doctors.models import Doctors
from medicine.models import Medical
from regions.models import City, Region
class Istifadeci(models.Model):
    ROL_NUMAYENDE = 'numayende'
    ROL_MENECER = 'menecer'
    ROL_DIVIZIYA_REHB = 'diviziya_rehb'
    ROL_REHBER = 'rehber'

    ROL_CHOICES = [
        (ROL_NUMAYENDE, 'Tibbi Nümayəndə'),
        (ROL_MENECER, 'Menecer'),
        (ROL_DIVIZIYA_REHB, 'Diviziya Rəhbər'),
        (ROL_REHBER, 'Rəhbər'),
    ]

    # QRUP SEÇİMLƏRİ (Yeni)
    QRUP_1 = 'QRUP 1'
    QRUP_2 = 'QRUP 2'
    QRUP_CHOICES = [
        (QRUP_1, 'QRUP 1'),
        (QRUP_2, 'QRUP 2'),
    ]

    login = models.CharField(max_length=100, unique=True)
    sifre = models.CharField(max_length=255)
    ad = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ROL_NUMAYENDE)
    
    # YENİ: Qrup sahəsi əlavə edildi
    qrup = models.CharField(max_length=20, choices=QRUP_CHOICES, null=True, blank=True, verbose_name="Qrup")
    
    # bolgeler ManyToManyField eynilə qalır
    bolgeler = models.ManyToManyField(
        Region,  # Əgər Region eyni fayldadırsa dırnaqsız, fərqlidirsə dırnaqla yazın
        blank=True,
        db_table='istifadeci_bolgeleri',
        related_name='vizit_istifadeciler'
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

    # YENİ: Sessiyaya qrupu da əlavə edirik ki, hesablama funksiyasında istifadə edə bilək
    def session_dict(self):
        return {
            'istifadeci_id': self.pk,
            'ad': self.ad,
            'rol': self.rol,
            'qrup': self.qrup,  # 'QRUP 1' və ya 'QRUP 2' (və ya None)
            'bolge_ids': list(self.bolgeler.values_list('id', flat=True)),
        }


class Vizit(models.Model):
    MUNASIBAT_CHOICES = [
        ('Xatırlatma', 'Xatırlatma'),
        ('Annotasiya', 'Annotasiya'),
        ('Münasibət', 'Münasibət'),
        ('İş planı', 'İş planı'),
        ('Propaqanda', 'Propaqanda'),
        ('Razılaşma', 'Razılaşma'),

    ]

    istifadeci = models.ForeignKey(
        Istifadeci, on_delete=models.PROTECT, db_column='istifadeci_id', related_name='vizitler'
    )
    hekim = models.ForeignKey(
        Doctors, on_delete=models.SET_NULL, db_column='hekim_id', related_name='vizitler', null=True, blank=True
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



class AptekVizit(models.Model):
    user = models.ForeignKey(Istifadeci, on_delete=models.PROTECT, db_column='user_id', related_name='aptek_vizit')
    rayon = models.ForeignKey(City, on_delete=models.SET_NULL, db_column='rayon_id', related_name='aptek_vizit', null=True, blank=True)
    bolge = models.ForeignKey(Region, on_delete=models.PROTECT, db_column='bolge_id', related_name='aptek_vizit')
    aptek_ad = models.CharField(max_length=255)
    aptek_nomre = models.CharField(max_length=255, null=True, blank=True)
    tarix = models.DateField()
    vaxt = models.TimeField()
    qeyd = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AptekVizit'

    def __str__(self):
        return f'{self.aptek_ad} — {self.user.ad}'



class AptekVizitPreparat(models.Model):
    aptek_vizit = models.ForeignKey(AptekVizit, on_delete=models.CASCADE, db_column='aptek_vizit_id', related_name='preparatlar' , null=True, blank=True)
    preparat = models.ForeignKey(Medical, on_delete=models.PROTECT, db_column='preparat_id', related_name='aptek_vizitler')
    sorusulub = models.BooleanField(default=False)
    satilib = models.BooleanField(default=False)
    movcuddur = models.BooleanField(default=True)
    ref_vez = models.CharField(max_length=255, null=True, blank=True)
    aptek_iscisi = models.CharField(max_length=255, null=True, blank=True)
    qeyd = models.TextField(null=True, blank=True)