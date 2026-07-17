from django.db import migrations, models
import django.db.models.deletion


def create_default_depo_and_assign(apps, schema_editor):
    Depo = apps.get_model('aptek', 'Depo')
    Aptek = apps.get_model('aptek', 'Aptek')
    Qaime = apps.get_model('aptek', 'Qaime')
    AnbarHereket = apps.get_model('aptek', 'AnbarHereket')

    depo = Depo.objects.create(name='Əsas depo', is_default=True)
    Aptek.objects.filter(depo__isnull=True).update(depo=depo)
    Qaime.objects.filter(depo__isnull=True).update(depo=depo)
    AnbarHereket.objects.filter(depo__isnull=True).update(depo=depo)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('aptek', '0007_anbarhereket_qaime_cascade'),
        ('medicine', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Depo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Depo adı')),
                ('is_default', models.BooleanField(default=False, verbose_name='Əsas depo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Depo',
                'verbose_name_plural': 'Depolar',
                'ordering': ['-is_default', 'name'],
            },
        ),
        migrations.AddField(
            model_name='aptek',
            name='depo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='aptekler',
                to='aptek.depo',
            ),
        ),
        migrations.AddField(
            model_name='qaime',
            name='depo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='qaimeler',
                to='aptek.depo',
            ),
        ),
        migrations.AddField(
            model_name='anbarhereket',
            name='depo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='hereketler',
                to='aptek.depo',
            ),
        ),
        migrations.RunPython(create_default_depo_and_assign, noop_reverse),
        migrations.RemoveConstraint(
            model_name='qaime',
            name='unique_aptek_qaime_number_type',
        ),
        migrations.AddConstraint(
            model_name='aptek',
            constraint=models.UniqueConstraint(
                fields=('depo', 'name'),
                name='unique_depo_aptek_name',
            ),
        ),
        migrations.AddConstraint(
            model_name='qaime',
            constraint=models.UniqueConstraint(
                fields=('depo', 'aptek', 'number', 'document_type'),
                name='unique_depo_aptek_qaime_number_type',
            ),
        ),
    ]
