# doctors/management/commands/check_sequences.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = 'Check and fix all database sequences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix sequences (otherwise just check)',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking database sequences...")
        
        # Bütün modelləri avtomatik tap
        models = apps.get_models()
        
        results = {}
        fix_mode = options['fix']
        
        for model in models:
            try:
                table_name = model._meta.db_table
                
                with connection.cursor() as cursor:
                    # Sequence adını tap
                    cursor.execute(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                    seq_result = cursor.fetchone()
                    
                    if seq_result and seq_result[0]:
                        seq_name = seq_result[0]
                        
                        # Max ID-ni tap
                        cursor.execute(f"SELECT MAX(id) FROM {table_name}")
                        max_id_result = cursor.fetchone()[0]
                        max_id = max_id_result if max_id_result else 0
                        
                        # Sequence dəyərini al
                        cursor.execute(f"SELECT last_value FROM {seq_name}")
                        current_seq = cursor.fetchone()[0]
                        
                        # Nəticəni yadda saxla
                        if current_seq <= max_id:
                            if fix_mode:
                                # Sıfırla
                                new_seq = max_id + 10
                                cursor.execute(f"SELECT setval('{seq_name}', {new_seq})")
                                results[table_name] = f'FIXED: {current_seq} → {new_seq}'
                                self.stdout.write(
                                    self.style.WARNING(f'⚠️  {table_name}: FIXED {current_seq} → {new_seq}')
                                )
                            else:
                                results[table_name] = f'NEEDS FIX: {current_seq} <= {max_id}'
                                self.stdout.write(
                                    self.style.WARNING(f'⚠️  {table_name}: NEEDS FIX {current_seq} <= {max_id}')
                                )
                        else:
                            results[table_name] = f'OK: {current_seq} (max: {max_id})'
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ {table_name}: OK {current_seq} (max: {max_id})')
                            )
                    else:
                        results[table_name] = 'NO_SEQUENCE'
                        self.stdout.write(
                            self.style.NOTICE(f'ℹ️  {table_name}: No sequence found')
                        )
                        
            except Exception as e:
                results[table_name] = f'ERROR: {str(e)}'
                self.stdout.write(
                    self.style.ERROR(f'❌ {table_name}: ERROR - {str(e)}')
                )
        
        # Nəticə
        if fix_mode:
            fixed_count = sum(1 for r in results.values() if 'FIXED' in r)
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"📊 Nəticə: {fixed_count} sequence sıfırlandı")
            self.stdout.write("="*50)
        else:
            needs_fix_count = sum(1 for r in results.values() if 'NEEDS FIX' in r)
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"📊 Nəticə: {needs_fix_count} sequence sıfırlanmağa ehtiyac var")
            self.stdout.write("İcazə vermək üçün: python manage.py check_sequences --fix")
            self.stdout.write("="*50)