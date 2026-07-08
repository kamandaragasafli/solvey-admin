from django.db import migrations, models


def backfill_doc_date(apps, schema_editor):
    Qaime = apps.get_model('aptek', 'Qaime')
    AnbarHereket = apps.get_model('aptek', 'AnbarHereket')
    for qaime in Qaime.objects.filter(doc_date__isnull=True):
        movement = (
            AnbarHereket.objects.filter(qaime_id=qaime.id)
            .order_by('date')
            .values_list('date', flat=True)
            .first()
        )
        if movement:
            qaime.doc_date = movement
            qaime.save(update_fields=['doc_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('aptek', '0005_qaime_document_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='qaime',
            name='doc_date',
            field=models.DateField(blank=True, null=True, verbose_name='Sənəd tarixi'),
        ),
        migrations.RunPython(backfill_doc_date, migrations.RunPython.noop),
    ]
