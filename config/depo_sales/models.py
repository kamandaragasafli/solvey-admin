from django.db import models


class Depo(models.Model):
    """Depo modeli."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Depo"
        verbose_name_plural = "Depolar"

    def __str__(self) -> str:
        return self.name


class UploadedReport(models.Model):
    """Yüklənmiş 1C Excel faylı (bir ay/dövr üçün satış hesabatı)."""

    depo = models.ForeignKey(
        Depo,
        on_delete=models.PROTECT,
        related_name="reports",
        verbose_name="Depo",
    )
    report_date = models.DateField(verbose_name="Tarix")
    file = models.FileField(upload_to="depo_reports/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date", "-uploaded_at"]
        verbose_name = "Depo hesabatı"
        verbose_name_plural = "Depo hesabatları"

    def __str__(self) -> str:
        return f"{self.depo.name} — {self.report_date:%d.%m.%Y}"


class Drug(models.Model):
    """Dərman kataloqu — ad üzrə unikal, müxtəlif hesabatlar arasında paylaşılır."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Depo dərmanı"
        verbose_name_plural = "Depo dərmanları"

    def __str__(self) -> str:
        return self.name


class SalesRecord(models.Model):
    """Bir hesabat daxilində bir dərmanın bir şəhər üzrə satış sayı."""

    report = models.ForeignKey(UploadedReport, on_delete=models.CASCADE, related_name="records")
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name="records")
    city = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Depo satış qeydi"
        verbose_name_plural = "Depo satış qeydləri"
        constraints = [
            models.UniqueConstraint(
                fields=["report", "drug", "city"], name="unique_depo_report_drug_city"
            )
        ]
        indexes = [
            models.Index(fields=["report", "drug"]),
            models.Index(fields=["report", "city"]),
        ]

    def __str__(self) -> str:
        return f"{self.drug} / {self.city}: {self.quantity}"
