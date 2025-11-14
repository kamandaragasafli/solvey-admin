from django.db import models
from regions.models import Region , Hospital, City
import random
import string
from medicine.models import Medical
from decimal import Decimal as d
from django.db.models import Sum





class Doctors(models.Model):
    ad = models.CharField(max_length=100)
    
    GENDER_SECIMI = [
        ('Kişi', 'Kişi'),
        ('Qadın', 'Qadın'),
    ]

    KATEQORIYA_SECIMI = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ]
    DERECE_SECIMI = [
        ('VIP', 'ViP Dərəcə'),
        ('I', 'I Dərəcə'),
        ('II', 'II Dərəcə'),
        ('III', 'III Dərəcə'),
    ]
    İXTİSAS_SECIMI = [
        ('CA', 'CA'), ('TE', 'TE'), ('SU', 'SU'), ('TR', 'TR'),
        ('NE', 'NE'), ('PE', 'PE'), ('EN', 'EN'), ('GN', 'GN'),
        ('DE', 'DE'), ('OR', 'OR'), ('PS', 'PS'), ('UR', 'UR'),
        ('ON', 'ON'), ('RE', 'RE'), ('AL', 'AL'), ('END', 'END'),
        ('GA', 'GA'), ('LOR', 'LOR'), ('DV', 'DV'), ('NP', 'NP'),
        # əlavə ixtisaslar
        ('AN', 'AN'), ('AN/UR', 'AN/UR'), ('BE', 'BE'), ('CU', 'CU'),
        ('DZ', 'DZ'), ('EN-DİA', 'EN-DİA'), ('EN-RN', 'EN-RN'), ('EN-Z', 'EN-Z'),
        ('FL', 'FL'), ('FT', 'FT'), ('FZ', 'FZ'), ('GAS', 'GAS'),
        ('GE', 'GE'), ('HE', 'HE'), ('IN', 'IN'), ('KA', 'KA'),
        ('NEF', 'NEF'), ('NP-C', 'NP-C'), ('OF', 'OF'), ('PE-TE', 'PE-TE'),
        ('PED', 'PED'), ('PU', 'PU'), ('PUL', 'PUL'), ('RA', 'RA'),
        ('RE-PE', 'RE-PE'), ('REV', 'REV'), ('RV', 'RV'), ('SU-TP', 'SU-TP'),
        ('TP', 'TP'), ('UR-AN', 'UR-AN'), ('URO', 'URO'), ('URO-AND', 'URO-AND'),
        ('İN', 'İN')
    ]


    ixtisas = models.CharField(max_length=100, choices=İXTİSAS_SECIMI)
    kategoriya = models.CharField(max_length=10, choices=KATEQORIYA_SECIMI)
    derece = models.CharField(max_length=10, choices=DERECE_SECIMI, default="II")
    cinsiyyet = models.CharField(max_length=10, choices=GENDER_SECIMI, default="Kişi")

    bolge = models.ForeignKey(Region, on_delete=models.CASCADE ,related_name='doctors')
    city = models.ForeignKey(City, on_delete=models.CASCADE , blank=True, null=True)
    klinika = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    number = models.CharField(max_length=250, blank=True, null=True)

    barkod = models.CharField(max_length=10, unique=True, blank=True)

    razılaşma = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    # Hesabat üçün maliyyə sahələri
     
    previous_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hesablanan_miqdar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hekimden_silinen = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    datasiya = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    borc = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yekun_borc = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def avans(self):
        if not self.pk:
            return 0
        result = self.odenisler.filter(payment_type='Avans', is_closed=False).aggregate(total=Sum('pay'))
        return result['total'] or 0

    @property
    def investisiya(self):
        if not self.pk:
            return 0
        result = self.odenisler.filter(payment_type='İnvest', is_closed=False).aggregate(total=Sum('pay'))
        return result['total'] or 0

    @property
    def geriqaytarma(self):
        if not self.pk:
            return 0
        result = self.odenisler.filter(payment_type='Geri_qaytarma', is_closed=False).aggregate(total=Sum('pay'))
        return result['total'] or 0

    @property
    def umumi_odenis(self):
        if not self.pk:
            return 0
        result = self.odenisler.aggregate(total=Sum('pay'))
        return result['total'] or 0
    
    @property
    def cari_yekun_borc(self):
        """
        Bu, yalnız görünüş (display) üçündür.
        Real bazaya yazılmır, sadəcə hesablanıb göstərilir.
        """
        previous_debt = self.previous_debt or 0
        avans = self.avans or 0
        investisiya = self.investisiya or 0
        geriqaytarma = self.geriqaytarma or 0
        datasiya = self.datasiya or 0


        # Hesablama
        yekun = previous_debt + avans + investisiya + datasiya  - geriqaytarma
        return round(yekun, 2)


    def get_last_recipe(self):
        return self.recipe_set.order_by('-date').first()

    @property
    def cinsiyyet_from_name(self):
        if not self.ad:
            return "Naməlum"
        soyad = self.ad.strip().split()[0]
        return "Qadın" if soyad[-1].lower() == 'a' else "Kişi"

    def save(self, *args, **kwargs):
        # Cinsiyyəti avtomatik təyin et
        if self.ad:
            soyad = self.ad.strip().split()[0]
            self.cinsiyyet = "Qadın" if soyad[-1].lower() == 'a' else "Kişi"

        # Barkod avtomatik generasiya et (əgər yoxdursa)
        if not self.barkod:
            self.barkod = self.generate_barkod_for_region(self.bolge.region_name)

        # Sadəcə yaddaşa yaz
        super().save(*args, **kwargs)

    @staticmethod
    def generate_barkod_for_region(bolge_adi):
        """
        Bölgə adından 2 hərf + '-' + 5 rəqəm formatında barkod yaradır.
        Məsələn: BA-12345
        """
        filtered_letters = ''.join([ch.upper() for ch in bolge_adi if ch.isalpha()])
        prefix = (filtered_letters[:2] if len(filtered_letters) >= 2 else (filtered_letters + "X")[:2])

        while True:
            digits = ''.join(random.choices(string.digits, k=5))
            code = f"{prefix}-{digits}"
            if not Doctors.objects.filter(barkod=code).exists():
                return code

    def __str__(self):
        return self.ad

    class Meta:
        verbose_name = "Həkim"
        verbose_name_plural = "Həkimlər"


class Recipe(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    dr = models.ForeignKey(Doctors, on_delete=models.CASCADE, related_name='recipe')
    date = models.DateField()
    
    def __str__(self):
        return f"{self.dr.ad} - {self.date}"
    
    class Meta:
        verbose_name = "Resept"
        verbose_name_plural = "Reseptlər"


# doctors/models.py
class RecipeDrug(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='drugs')
    drug = models.ForeignKey(Medical, on_delete=models.CASCADE)
    number = models.DecimalField(max_digits=5, decimal_places=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.drug.med_name} ({self.number})"
    
    class Meta:
        verbose_name = "Resept Dərmanı"
        verbose_name_plural = "Reseptdəki Dərmanlar"

class RealSales(models.Model):
    region_n = models.ForeignKey(Region, on_delete=models.CASCADE)
    dr_name = models.ForeignKey(Doctors, on_delete=models.CASCADE)
    date_sale = models.DateField()
    
    def __str__(self):
        return f"{self.dr_name.ad} - {self.date_sale}"
    
    class Meta:
        verbose_name = "Real Satış"
        verbose_name_plural = "Real Satışlar"


class RealSalesDrug(models.Model):
    real_sale = models.ForeignKey(RealSales, on_delete=models.CASCADE, related_name='drug_name')
    drug_name = models.ForeignKey(Medical, on_delete=models.CASCADE)
    numbers = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.drug_name.med_name} ({self.numbers})"
    
    class Meta:
        verbose_name = "Real Satış Dərmanı"
        verbose_name_plural = "Real Satış Dərmanları"

