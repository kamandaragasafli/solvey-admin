from django.db import models

from medicine.models import Medical


class Depo(models.Model):
    name = models.CharField(max_length=250, verbose_name='Depo adı')
    is_default = models.BooleanField(default=False, verbose_name='Əsas depo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Depo'
        verbose_name_plural = 'Depolar'
        ordering = ['-is_default', 'name']

    def __str__(self):
        return self.name


class Aptek(models.Model):
    depo = models.ForeignKey(
        Depo, on_delete=models.CASCADE, related_name='aptekler', null=True, blank=True
    )
    name = models.CharField(max_length=250, verbose_name='Aptek adı')

    class Meta:
        verbose_name = 'Aptek'
        verbose_name_plural = 'Apteklər'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['depo', 'name'],
                name='unique_depo_aptek_name',
            ),
        ]

    def __str__(self):
        return self.name


class Qaime(models.Model):
    DOC_QAIME = 'qaime'
    DOC_RETURN = 'geri_qaytarma'
    DOCUMENT_TYPES = [
        (DOC_QAIME, 'Qaimə'),
        (DOC_RETURN, 'Geri qaytarma'),
    ]

    depo = models.ForeignKey(
        Depo, on_delete=models.CASCADE, related_name='qaimeler', null=True, blank=True
    )
    aptek = models.ForeignKey(Aptek, on_delete=models.CASCADE, related_name='qaimeler')
    number = models.PositiveIntegerField(verbose_name='Qaimə №')
    document_type = models.CharField(
        max_length=20, choices=DOCUMENT_TYPES, default=DOC_QAIME, verbose_name='Sənəd növü'
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pdf = models.FileField(upload_to='qaimeler/', null=True, blank=True)
    doc_date = models.DateField(verbose_name='Sənəd tarixi', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Qaimə'
        verbose_name_plural = 'Qaimələr'
        ordering = ['-doc_date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['depo', 'aptek', 'number', 'document_type'],
                name='unique_depo_aptek_qaime_number_type',
            ),
        ]

    def __str__(self):
        return f'Qaimə №{self.number} — {self.aptek.name}'


class AnbarHereket(models.Model):
    MOVEMENT_IN = 'in'
    MOVEMENT_OUT = 'out'
    MOVEMENT_TYPES = [
        (MOVEMENT_IN, 'Giriş'),
        (MOVEMENT_OUT, 'Çıxış'),
    ]

    depo = models.ForeignKey(
        Depo, on_delete=models.CASCADE, related_name='hereketler', null=True, blank=True
    )
    drug = models.ForeignKey(Medical, on_delete=models.CASCADE, related_name='anbar_hereketleri')
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    aptek = models.ForeignKey(
        Aptek, on_delete=models.SET_NULL, null=True, blank=True, related_name='anbar_hereketleri'
    )
    qaime = models.ForeignKey(
        Qaime, on_delete=models.CASCADE, null=True, blank=True, related_name='hereketler'
    )
    note = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anbar hərəkəti'
        verbose_name_plural = 'Anbar hərəkətləri'
        ordering = ['-date', '-id']

    def __str__(self):
        sign = '+' if self.movement_type == self.MOVEMENT_IN else '−'
        return f'{self.drug.med_name} {sign}{self.quantity} ({self.date})'



class DrugPrice(models.Model):
    depo = models.ForeignKey(
        Depo,
        on_delete=models.CASCADE,
        related_name='drug_prices',
        null=True,
        blank=True,
        verbose_name='Anbar',
    )
    drug = models.ForeignKey(Medical, on_delete=models.CASCADE, related_name='drug_prices')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Qiymət')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='SKT')
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'Dərman qiyməti'
        verbose_name_plural = 'Dərman qiymətləri'
        ordering = ['drug__med_name']
        constraints = [
            models.UniqueConstraint(
                fields=['depo', 'drug'],
                name='unique_depo_drug_price',
            ),
        ]

    def __str__(self):
        return f'{self.drug.med_name} — {self.price}'
