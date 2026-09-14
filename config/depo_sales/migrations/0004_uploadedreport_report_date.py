# Generated manually for report_date

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("depo_sales", "0003_uploadedreport_depo"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadedreport",
            name="report_date",
            field=models.DateField(
                default=datetime.date.today,
                verbose_name="Tarix",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="uploadedreport",
            options={
                "ordering": ["-report_date", "-uploaded_at"],
                "verbose_name": "Depo hesabatı",
                "verbose_name_plural": "Depo hesabatları",
            },
        ),
    ]
