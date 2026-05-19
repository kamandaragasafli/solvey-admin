# Sinxronizasiya Modulu — JSON API versiyası

## Necə işləyir?

```
Kənar server (Django / PostgreSQL)     Sizin server (MySQL)
  http://64.226.72.85                    karfa495_vizit
  /api/hekimler/?key=...    →→→          kx_hekimler
                                         kx_bolgeler
                                         kx_rayonlar
                                         kx_muessiseler
```

---

## Quraşdırma — 3 addım

### 1. Kənar serverdəki adama `KENAR_SERVER_ucun_kod.py` faylını göndər
O, `views.py` və `urls.py`-a həmin kodu əlavə edir.
Test: http://64.226.72.85/api/hekimler/?key=SolveyApi2024

### 2. kx_ cədvəllərini yaradın
phpMyAdmin → `karfa495_vizit` → Import → `sync/kx_tables.sql`
(Sinxronizasiya skripti özü də yaradır, amma əvvəlcədən etmək daha etibarlıdır)

### 3. Sinxronizasiyanı işlədin
Brauzerdən:
  https://solveymax.net/vizit/sync/sync_hekimler.php?key=SolveySync2024

Cron ilə (hər gün saat 06:00):
  0 6 * * * php /home/karfa495/public_html/vizit/sync/sync_hekimler.php

---

## Fayllar

| Fayl | Məqsəd |
|------|--------|
| `sync_hekimler.php`       | Əsas sinxronizasiya skripti |
| `kx_tables.sql`           | kx_ cədvəllərini əl ilə yaratmaq üçün |
| `hekim_query.php`         | Həkim sorğusu köməkçisi (ajax.php tərəfindən istifadə olunur) |
| `KENAR_SERVER_ucun_kod.py`| Kənar Django serverə əlavə edilməli Python kodu |

---

## Sinxronizasiya nə edir?

- API-dən yalnız `is_active=True` həkimləri çəkir
- `pg_id` ilə UPSERT edir — təkrar işlətmək tamamilə təhlükəsizdir
- Bölgə, rayon, müəssisəni avtomatik yaradır
- Dəyişikliklər növbəti sinxronizasiyada avtomatik əks olunur
