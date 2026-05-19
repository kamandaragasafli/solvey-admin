<?php
/**
 * Solvey Pharma — Həkim Sinxronizasiya Skripti (JSON API versiyası)
 * 
 * Kənar Django serverindən JSON API ilə həkim datasını çəkir,
 * yerli MySQL-ə yazır.
 *
 * Brauzer: https://solveymax.net/vizit/sync/sync_hekimler.php?key=SolveySync2024
 * Cron:    0 6 * * * php /path/vizit/sync/sync_hekimler.php
 */

if (PHP_SAPI !== 'cli') {
    if (($_GET['key'] ?? '') !== 'SolveySync2024') {
        http_response_code(403); die('403 Forbidden');
    }
    header('Content-Type: text/plain; charset=utf-8');
}

define('SYNC_START', microtime(true));

// ── KONFIQURASIYA ─────────────────────────────────────────────────
define('API_URL', 'http://64.226.72.85/api/hekimler/?key=SolveyApi2024');
define('API_TIMEOUT', 30); // saniyə

$MYSQL = [
    'host'    => 'localhost',
    'dbname'  => 'karfa495_vizit',
    'user'    => 'karfa495_vizit',
    'pass'    => 'Kamran97mecnunov97',
    'charset' => 'utf8mb4',
];

// ── LOG ───────────────────────────────────────────────────────────
function log_msg(string $msg): void {
    echo '[' . date('Y-m-d H:i:s') . '] ' . $msg . "\n";
    flush();
}

log_msg('=== Sinxronizasiya başlandı ===');

// ── API-DƏN DATA ÇƏK ─────────────────────────────────────────────
log_msg('📡 Kənar serverdən data çəkilir → ' . API_URL);

$ctx = stream_context_create(['http' => [
    'timeout' => API_TIMEOUT,
    'method'  => 'GET',
    'header'  => "Accept: application/json\r\n",
]]);

$raw = @file_get_contents(API_URL, false, $ctx);

if ($raw === false) {
    log_msg('❌ XƏTA: API-yə qoşulmaq mümkün olmadı.');
    log_msg('   URL: ' . API_URL);
    log_msg('   Kənar serverin işlədiyini və API endpoint-in aktiv olduğunu yoxlayın.');
    exit(1);
}

$hekimler = json_decode($raw, true);

if (!is_array($hekimler)) {
    log_msg('❌ XƏTA: API-dən gələn cavab JSON deyil.');
    log_msg('   Cavabın ilk 300 simvolu: ' . substr($raw, 0, 300));
    exit(1);
}

$count = count($hekimler);
log_msg("✅ API-dən {$count} həkim gəldi.");

if ($count === 0) {
    log_msg('⚠️  Həkim tapılmadı. Sinxronizasiya dayandırıldı.');
    exit(0);
}

// ── MYSQL BAĞLANTISI ──────────────────────────────────────────────
try {
    $pdo = new PDO(
        "mysql:host={$MYSQL['host']};dbname={$MYSQL['dbname']};charset={$MYSQL['charset']}",
        $MYSQL['user'], $MYSQL['pass'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
         PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
    );
    log_msg("✅ MySQL bağlantısı quruldu.");
} catch (PDOException $e) {
    log_msg('❌ MySQL XƏTA: ' . $e->getMessage());
    exit(1);
}

// ── CƏDVƏLLƏRİ HAZIRLA ───────────────────────────────────────────
$pdo->exec("
    CREATE TABLE IF NOT EXISTS `kx_bolgeler` (
        `id` int AUTO_INCREMENT PRIMARY KEY,
        `ad` varchar(150) NOT NULL,
        `nov` varchar(50) DEFAULT NULL,
        UNIQUE KEY `ad` (`ad`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
");
$pdo->exec("
    CREATE TABLE IF NOT EXISTS `kx_rayonlar` (
        `id` int AUTO_INCREMENT PRIMARY KEY,
        `ad` varchar(150) NOT NULL,
        `bolge_id` int NOT NULL,
        UNIQUE KEY `ad_bolge` (`ad`,`bolge_id`),
        KEY `bolge_id` (`bolge_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
");
$pdo->exec("
    CREATE TABLE IF NOT EXISTS `kx_muessiseler` (
        `id` int AUTO_INCREMENT PRIMARY KEY,
        `ad` varchar(200) NOT NULL,
        `bolge_id` int NOT NULL,
        UNIQUE KEY `ad_bolge` (`ad`,`bolge_id`),
        KEY `bolge_id` (`bolge_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
");
$pdo->exec("
    CREATE TABLE IF NOT EXISTS `kx_hekimler` (
        `id` int AUTO_INCREMENT PRIMARY KEY,
        `pg_id` int NOT NULL UNIQUE COMMENT 'Kənar serverdəki ID',
        `ad_soyad` varchar(200) NOT NULL,
        `ixtisas_kod` varchar(20) DEFAULT NULL,
        `kateqoriya` varchar(10) DEFAULT NULL,
        `derece` varchar(20) DEFAULT NULL,
        `cinsiyyet` varchar(10) DEFAULT NULL,
        `bolge_id` int DEFAULT NULL,
        `rayon_id` int DEFAULT NULL,
        `muessise_id` int DEFAULT NULL,
        `son_sinx` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY `bolge_id` (`bolge_id`),
        KEY `rayon_id` (`rayon_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
");
log_msg('✅ kx_* cədvəlləri hazırdır.');

// ── UPSERT ───────────────────────────────────────────────────────
$stmtBolge = $pdo->prepare("
    INSERT INTO kx_bolgeler (ad) VALUES (?)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
");
$stmtRayon = $pdo->prepare("
    INSERT INTO kx_rayonlar (ad, bolge_id) VALUES (?,?)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
");
$stmtMuessise = $pdo->prepare("
    INSERT INTO kx_muessiseler (ad, bolge_id) VALUES (?,?)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
");
$stmtHekim = $pdo->prepare("
    INSERT INTO kx_hekimler
        (pg_id, ad_soyad, ixtisas_kod, kateqoriya, derece, cinsiyyet, bolge_id, rayon_id, muessise_id)
    VALUES (?,?,?,?,?,?,?,?,?)
    ON DUPLICATE KEY UPDATE
        ad_soyad=VALUES(ad_soyad),
        ixtisas_kod=VALUES(ixtisas_kod),
        kateqoriya=VALUES(kateqoriya),
        derece=VALUES(derece),
        cinsiyyet=VALUES(cinsiyyet),
        bolge_id=VALUES(bolge_id),
        rayon_id=VALUES(rayon_id),
        muessise_id=VALUES(muessise_id),
        son_sinx=CURRENT_TIMESTAMP
");

$bolgeCache    = [];
$rayonCache    = [];
$muessiseCache = [];
$stats = ['yeni' => 0, 'yenilendi' => 0, 'xeta' => 0];

$pdo->beginTransaction();
try {
    foreach ($hekimler as $h) {

        // API sahə adları (Django annotate ilə gəlir):
        // id, ad, ixtisas, kategoriya, derece, cinsiyyet,
        // bolge__region_name, city__city_name, klinika__hospital_name

        $pg_id      = (int)($h['id'] ?? 0);
        $ad_soyad   = trim($h['ad'] ?? '');
        $ixtisas    = trim($h['ixtisas'] ?? '');
        $kateqoriya = trim($h['kategoriya'] ?? '');
        $derece     = trim($h['derece'] ?? '');
        $cinsiyyet  = trim($h['cinsiyyet'] ?? '');
        $bolge_ad   = trim($h['bolge__region_name'] ?? '');
        $rayon_ad   = trim($h['city__city_name'] ?? '');
        $muessise_ad= trim($h['klinika__hospital_name'] ?? '');

        if (!$pg_id || !$ad_soyad || !$bolge_ad) {
            $stats['xeta']++;
            continue;
        }

        // Bölgə
        if (!isset($bolgeCache[$bolge_ad])) {
            $stmtBolge->execute([$bolge_ad]);
            $bolgeCache[$bolge_ad] = (int)$pdo->lastInsertId();
        }
        $bolge_id = $bolgeCache[$bolge_ad];

        // Rayon
        $rayon_id = null;
        if ($rayon_ad !== '') {
            $rKey = $rayon_ad . '|' . $bolge_id;
            if (!isset($rayonCache[$rKey])) {
                $stmtRayon->execute([$rayon_ad, $bolge_id]);
                $rayonCache[$rKey] = (int)$pdo->lastInsertId();
            }
            $rayon_id = $rayonCache[$rKey];
        }

        // Müəssisə
        $muessise_id = null;
        if ($muessise_ad !== '') {
            $mKey = $muessise_ad . '|' . $bolge_id;
            if (!isset($muessiseCache[$mKey])) {
                $stmtMuessise->execute([$muessise_ad, $bolge_id]);
                $muessiseCache[$mKey] = (int)$pdo->lastInsertId();
            }
            $muessise_id = $muessiseCache[$mKey];
        }

        // Həkim
        $before = $pdo->lastInsertId();
        $stmtHekim->execute([
            $pg_id, $ad_soyad, $ixtisas, $kateqoriya,
            $derece, $cinsiyyet, $bolge_id, $rayon_id, $muessise_id
        ]);
        $after = $pdo->lastInsertId();
        if ($after && $after !== $before) $stats['yeni']++;
        else $stats['yenilendi']++;
    }
    $pdo->commit();
} catch (Exception $e) {
    $pdo->rollBack();
    log_msg('❌ Tranzaksiya xətası: ' . $e->getMessage());
    exit(1);
}

// ── NƏTİCƏ ───────────────────────────────────────────────────────
$elapsed = round(microtime(true) - SYNC_START, 2);
log_msg('─────────────────────────────────');
log_msg("✅ Yeni həkim:      {$stats['yeni']}");
log_msg("🔄 Yenilənən:       {$stats['yenilendi']}");
log_msg("⚠️  Keçilən (xəta): {$stats['xeta']}");
log_msg("⏱  Vaxt: {$elapsed} san.");
log_msg('=== Sinxronizasiya tamamlandı ===');
