from django.core.management.base import BaseCommand

from aptek.services import purge_qaime_pdfs


class Command(BaseCommand):
    help = (
        'Delete qaime PDF files older than retention (default 30 days). '
        'DB rows are kept. Use --all to delete every PDF file.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Delete PDFs older than N days (default: APTEK_QAIME_PDF_RETENTION_DAYS).',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete all qaime PDF files.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show count without deleting.',
        )

    def handle(self, *args, **options):
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        from aptek.models import Qaime

        days = options['days']
        delete_all = options['all']
        dry_run = options['dry_run']

        if days is None and not delete_all:
            days = int(getattr(settings, 'APTEK_QAIME_PDF_RETENTION_DAYS', 30))

        qs = Qaime.objects.exclude(pdf='').exclude(pdf__isnull=True)
        if not delete_all:
            qs = qs.filter(created_at__lt=timezone.now() - timedelta(days=days))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'Dry-run: {qs.count()} PDF file(s) would be deleted.')
            )
            return

        if delete_all:
            result = purge_qaime_pdfs(all_files=True)
        else:
            result = purge_qaime_pdfs(older_than_days=days)

        mb = result['freed_bytes'] / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {result["removed"]} PDF file(s), freed {mb:.1f} MB.'
            )
        )
