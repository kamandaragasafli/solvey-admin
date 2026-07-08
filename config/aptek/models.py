from django.db import models

from medicine.models import Medical


class Aptek(models.Model):
    name = models.CharField(max_length=250, verbose_name='Aptek adı')

    class Meta:
        verbose_name = 'Aptek'
        verbose_name_plural = 'Apteklər'
        ordering = ['name']

    def __str__(self):
        return self.name


class Qaime(models.Model):
    DOC_QAIME = 'qaime'
    DOC_RETURN = 'geri_qaytarma'
    DOCUMENT_TYPES = [
        (DOC_QAIME, 'Qaimə'),
        (DOC_RETURN, 'Geri qaytarma'),
    ]

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
                fields=['aptek', 'number', 'document_type'],
                name='unique_aptek_qaime_number_type',
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

    drug = models.ForeignKey(Medical, on_delete=models.CASCADE, related_name='anbar_hereketleri')
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    aptek = models.ForeignKey(
        Aptek, on_delete=models.SET_NULL, null=True, blank=True, related_name='anbar_hereketleri'
    )
    qaime = models.ForeignKey(
        Qaime, on_delete=models.SET_NULL, null=True, blank=True, related_name='hereketler'
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
