<!DOCTYPE html>
<html lang="az">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title><?= isset($pageTitle) ? htmlspecialchars($pageTitle).' | ' : '' ?>Solvey Pharma</title>
<link rel="stylesheet" href="<?= BASE_URL ?>css/style.css">
</head>
<body>
<?php $user = cariIstifadeci(); ?>
<header class="site-header">
    <div class="header-inner">
        <div class="logo">
            <span class="logo-icon">💊</span>
            <div>
                <strong>Solvey Pharma</strong>
                <small>Vizit İdarəetmə Sistemi</small>
            </div>
        </div>
        <nav>
            <a href="<?= BASE_URL ?>index.php" class="<?= basename($_SERVER['PHP_SELF'])=='index.php'?'active':'' ?>">🏠 Ana Səhifə</a>
            <?php if (in_array($user['rol'], ['menecer','rehber'])): ?>
            <a href="<?= BASE_URL ?>bolge_stat.php" class="<?= basename($_SERVER['PHP_SELF'])=='bolge_stat.php'?'active':'' ?>">📍 Bölgə Stat.</a>
            <?php endif; ?>
            <a href="<?= BASE_URL ?>hesabat.php" class="<?= basename($_SERVER['PHP_SELF'])=='hesabat.php'?'active':'' ?>">📊 Hesabat</a>
            <?php if ($user['rol']==='rehber'): ?>
            <a href="<?= BASE_URL ?>admin.php" class="<?= basename($_SERVER['PHP_SELF'])=='admin.php'?'active':'' ?>">⚙️ Admin</a>
            <?php endif; ?>
        </nav>
        <div class="user-info">
            <span class="role-badge role-<?= $user['rol'] ?>"><?= rolAd($user['rol']) ?></span>
            <span style="font-size:14px;color:rgba(255,255,255,.85);"><?= htmlspecialchars($user['ad']) ?></span>
            <a href="<?= BASE_URL ?>logout.php" class="btn-logout">Çıxış</a>
        </div>
    </div>
</header>
<main class="container">
