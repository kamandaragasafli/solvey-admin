# doctors/utils.py
from django.db import connection

def fix_recipe_drug_sequence():
    """RecipeDrug sequence'ini sıfırla"""
    try:
        with connection.cursor() as cursor:
            # Sequence adını tap
            cursor.execute("SELECT pg_get_serial_sequence('doctors_recipedrug', 'id')")
            seq_name = cursor.fetchone()[0]
            
            if seq_name:
                # Max ID-ni tap və sequence'i sıfırla
                cursor.execute("SELECT MAX(id) FROM doctors_recipedrug")
                max_id = cursor.fetchone()[0] or 0
                cursor.execute(f"SELECT setval('{seq_name}', {max_id + 1})")
                print(f"RecipeDrug sequence fixed: {seq_name} -> {max_id + 1}")
                return True
    except Exception as e:
        print(f"Sequence fix error: {e}")
    return False

def fix_all_sequences():
    """Bütün əsas modellərin sequence'lərini yoxla və sıfırla"""
    tables = [
        'doctors_recipedrug',
        'doctors_recipe', 
        'doctors_doctors',
        'doctors_region',
        'doctors_medical'
    ]
    
    results = {}
    
    for table in tables:
        try:
            with connection.cursor() as cursor:
                # Sequence adını tap
                cursor.execute(f"SELECT pg_get_serial_sequence('{table}', 'id')")
                seq_result = cursor.fetchone()
                
                if seq_result and seq_result[0]:
                    seq_name = seq_result[0]
                    
                    # Max ID-ni tap
                    cursor.execute(f"SELECT MAX(id) FROM {table}")
                    max_id_result = cursor.fetchone()[0]
                    max_id = max_id_result if max_id_result else 0
                    
                    # Sequence dəyərini al
                    cursor.execute(f"SELECT last_value FROM {seq_name}")
                    current_seq = cursor.fetchone()[0]
                    
                    # Lazımsa sıfırla
                    if current_seq <= max_id:
                        new_seq = max_id + 10
                        cursor.execute(f"SELECT setval('{seq_name}', {new_seq})")
                        results[table] = f"Fixed: {current_seq} -> {new_seq}"
                    else:
                        results[table] = f"OK: {current_seq} (max: {max_id})"
                else:
                    results[table] = "No sequence found"
                    
        except Exception as e:
            results[table] = f"Error: {str(e)}"
    
    return results