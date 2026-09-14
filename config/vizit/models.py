import hashlib

from django.db import models

from doctors.models import Doctors
from medicine.models import Medical
from regions.models import City, Region
from datetime import timedelta


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
    aptek_vizit = models.ForeignKey(AptekVizit, on_delete=models.CASCADE, db_column='aptek_vizit_id',
                                    related_name='preparatlar', null=True, blank=True)
    preparat = models.ForeignKey(Medical, on_delete=models.PROTECT, db_column='preparat_id',
                                 related_name='aptek_vizitler')
    sorusulub = models.BooleanField(default=False)
    satilib = models.BooleanField(default=False)
    movcuddur = models.BooleanField(default=True)
    ref_vez = models.CharField(max_length=255, null=True, blank=True)
    aptek_iscisi = models.CharField(max_length=255, null=True, blank=True)
    qeyd = models.TextField(null=True, blank=True)


class DayRecipe(models.Model):
    dr = models.ForeignKey(Doctors, on_delete=models.SET_NULL, db_column='dr_id', related_name='day_recipes',
                           null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, db_column='region_id', related_name='day_recipes')
    created_by = models.ForeignKey(Istifadeci, on_delete=models.SET_NULL, db_column='created_by_id',
                                   related_name='day_recipes', null=True, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'day_recipes'

    def __str__(self):
        return f'DayRecipe #{self.pk} — {self.dr.ad if self.dr else "N/A"}'


class DayRecipeDrug(models.Model):
    recipe = models.ForeignKey(DayRecipe, on_delete=models.CASCADE, db_column='recipe_id', related_name='drugs')
    drug = models.ForeignKey(Medical, on_delete=models.PROTECT, db_column='drug_id', related_name='day_recipe_drugs')
    number = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'day_recipe_drugs'

    def __str__(self):
        return f'{self.recipe_id} — {self.drug.med_name} — {self.number}'


class WeeklySchedule(models.Model):
    """Həftəlik qrafiq (Bazar ertəsi–Cümə)."""

    week_start = models.DateField(verbose_name="Həftə başlanğıcı (B.e.)")
    created_by = models.ForeignKey(
        Istifadeci,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_schedules",
        db_column="created_by_id",
    )
    menecer_name = models.CharField(max_length=150, blank=True, verbose_name="Menecer")
    sedr_name = models.CharField(max_length=150, blank=True, verbose_name="İdarə heyətinin sədri")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "weekly_schedules"
        ordering = ["-week_start", "-id"]
        verbose_name = "Həftəlik qrafiq"
        verbose_name_plural = "Həftəlik qrafiklər"

    def __str__(self):
        return f"Qrafiq {self.week_start:%d.%m.%Y}"

    @property
    def week_end(self):
        return self.week_start + timedelta(days=4)

class WeeklyScheduleDay(models.Model):
    WEEKDAY_CHOICES = [
        (1, "Bazar ertəsi"),
        (2, "Çərşənbə axşamı"),
        (3, "Çərşənbə"),
        (4, "Cümə axşamı"),
        (5, "Cümə"),
    ]

    schedule = models.ForeignKey(
        WeeklySchedule,
        on_delete=models.CASCADE,
        related_name="days",
        db_column="schedule_id",
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_schedule_days",
        db_column="region_id",
        verbose_name="Bölgə",
    )
    qrafik = models.CharField(max_length=150, blank=True, verbose_name="Qrafik")
    tn = models.CharField(max_length=100, blank=True, verbose_name="T/N")

    class Meta:
        db_table = "weekly_schedule_days"
        ordering = ["weekday"]
        unique_together = [("schedule", "weekday")]
        verbose_name = "Qrafik günü"
        verbose_name_plural = "Qrafik günləri"

    def __str__(self):
        return f"{self.get_weekday_display()} — {self.qrafik or '—'}"


class WeeklyScheduleVisit(models.Model):
    day = models.ForeignKey(
        WeeklyScheduleDay,
        on_delete=models.CASCADE,
        related_name="visits",
        db_column="day_id",
    )
    place_name = models.CharField(max_length=255, verbose_name="Yer / klinika")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "weekly_schedule_visits"
        ordering = ["position", "id"]
        verbose_name = "Qrafik viziti"
        verbose_name_plural = "Qrafik vizitləri"

    def __str__(self):
        return self.place_name


class GorulenHekim(models.Model):
    """Nümayəndənin bölgədə gördüyü həkim (günlük)."""

    istifadeci = models.ForeignKey(
        Istifadeci,
        on_delete=models.CASCADE,
        related_name="gorulen_hekimler",
        db_column="istifadeci_id",
    )
    hekim = models.ForeignKey(
        Doctors,
        on_delete=models.CASCADE,
        related_name="gorulme_qeydleri",
        db_column="hekim_id",
    )
    bolge = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="gorulen_hekimler",
        db_column="bolge_id",
    )
    seen_date = models.DateField(verbose_name="Tarix")
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gorulen_hekimler"
        ordering = ["-seen_at"]
        unique_together = [("istifadeci", "hekim", "seen_date")]
        verbose_name = "Görülən həkim"
        verbose_name_plural = "Görülən həkimlər"

    def __str__(self):
        return f"{self.hekim} — {self.seen_date}"
