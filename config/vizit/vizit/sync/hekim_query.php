<?php
/**
 * Həkim sorğusu üçün köməkçi funksiya.
 * 
 * Əgər kx_hekimler cədvəli mövcuddursa və dolu isə → kənar serverdən çəkilmiş data
 * Əks halda → yerli hekimler cədvəlindən (köhnə üsul)
 */

function getHekimlerByRayon(PDO $pdo, int $rayon_id, ?int $bolge_id = null): array
{
    // Kənar serverdən sinxronizasiya var?
    try {
        $check = $pdo->query("SELECT COUNT(*) FROM kx_hekimler")->fetchColumn();
    } catch (Exception $e) {
        $check = 0;
    }

    if ($check > 0) {
        // kx_hekimler cədvəlindən — rayon adına görə uyğunlaşdır
        // kx_rayonlar.ad = rayonlar.ad əlaqəsi ilə
        $stmt = $pdo->prepare("
            SELECT
                kh.id,
                kh.pg_id,
                kh.ad_soyad,
                kh.ixtisas_kod,
                kh.derece         AS kateqoriya,
                kh.cinsiyyet,
                kb.ad             AS bolge,
                COALESCE(kr.ad,'') AS rayon,
                km.ad             AS muessise
            FROM kx_hekimler kh
            LEFT JOIN kx_bolgeler   kb ON kb.id = kh.bolge_id
            LEFT JOIN kx_rayonlar   kr ON kr.id = kh.rayon_id
            LEFT JOIN kx_muessiseler km ON km.id = kh.muessise_id
            WHERE kh.rayon_id IN (
                SELECT kxr.id FROM kx_rayonlar kxr
                JOIN rayonlar r ON r.ad = kxr.ad
                WHERE r.id = ?
            )
            ORDER BY kh.ad_soyad
        ");
        $stmt->execute([$rayon_id]);
        return $stmt->fetchAll();
    }

    // Fallback: yerli cədvəl
    $stmt = $pdo->prepare("
        SELECT h.id, h.ad_soyad,
               COALESCE(i.kod,'') AS ixtisas_kod,
               COALESCE(k.ad,'') AS kateqoriya,
               '' AS derece, '' AS cinsiyyet,
               '' AS muessise
        FROM hekimler h
        LEFT JOIN ixtisaslar i ON i.id = h.ixtisas_id
        LEFT JOIN kateqoriyalar k ON k.id = h.kateqoriya_id
        WHERE h.rayon_id = ?
        ORDER BY h.ad_soyad
    ");
    $stmt->execute([$rayon_id]);
    return $stmt->fetchAll();
}


function getBolgeHekimSayı(PDO $pdo, int $bolge_id, string $tarix_bas, string $tarix_son): array
{
    // Sinxronizasiya varsa kx_ cədvəlindən istifadə et
    try {
        $check = $pdo->query("SELECT COUNT(*) FROM kx_hekimler")->fetchColumn();
    } catch (Exception $e) {
        $check = 0;
    }

    if ($check > 0) {
        $stmt = $pdo->prepare("
            SELECT
                u.ad AS numayende,
                COUNT(v.id) AS vizit_sayi,
                GROUP_CONCAT(DISTINCT r.ad ORDER BY r.ad SEPARATOR ', ') AS rayonlar
            FROM vizitler v
            JOIN istifadeciler u ON u.id = v.istifadeci_id
            JOIN rayonlar r ON r.id = v.rayon_id
            WHERE v.bolge_id = ? AND v.tarix BETWEEN ? AND ?
            GROUP BY u.id
            ORDER BY vizit_sayi DESC
        ");
        $stmt->execute([$bolge_id, $tarix_bas, $tarix_son]);
        return $stmt->fetchAll();
    }

    // Fallback
    return [];
}
