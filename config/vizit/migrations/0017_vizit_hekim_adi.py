from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vizit', '0016_gorulen_hekim'),
    ]

    operations = [
        migrations.AddField(
            model_name='vizit',
            name='hekim_adi',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='vizit',
            name='hekim_ixtisas',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
