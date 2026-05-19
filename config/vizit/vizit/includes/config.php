<?php
define('DB_HOST', 'localhost');
define('DB_NAME', 'karfa495_vizit');
define('DB_USER', 'karfa495_vizit');
define('DB_PASS', 'Kamran97mecnunov97');
define('DB_CHARSET', 'utf8mb4');
define('BASE_URL', '/vizit/');

try {
    $pdo = new PDO(
        "mysql:host=".DB_HOST.";dbname=".DB_NAME.";charset=".DB_CHARSET,
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,
         PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,
         PDO::ATTR_EMULATE_PREPARES=>false]
    );
} catch (PDOException $e) {
    die('<div style="padding:20px;background:#f8d7da;color:#721c24;font-family:sans-serif;"><h3>Verilənlər bazasına qoşulmaq mümkün olmadı</h3><p>'.htmlspecialchars($e->getMessage()).'</p></div>');
}

// ── SESSION & AUTH ────────────────────────────────────────────────
if (session_status() === PHP_SESSION_NONE) session_start();

function girisYoxla() {
    if (empty($_SESSION['istifadeci_id'])) {
        header('Location: '.BASE_URL.'login.php');
        exit;
    }
}

function rolYoxla(array $icazeli_roller) {
    if (!in_array($_SESSION['rol'] ?? '', $icazeli_roller)) {
        header('Location: '.BASE_URL.'index.php');
        exit;
    }
}

function cariIstifadeci(): array {
    return [
        'id'       => $_SESSION['istifadeci_id'] ?? 0,
        'ad'       => $_SESSION['ad']             ?? '',
        'rol'      => $_SESSION['rol']            ?? '',
        'bolge_id' => $_SESSION['bolge_id']       ?? null,
    ];
}

function rolAd(string $rol): string {
    return match($rol) {
        'numayende' => 'Tibbi Nümayəndə',
        'menecer'   => 'Menecer',
        'rehber'    => 'Rəhbər',
        default     => $rol,
    };
}
