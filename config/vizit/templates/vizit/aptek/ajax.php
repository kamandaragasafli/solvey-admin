<?php
require_once __DIR__.'/includes/config.php';
girisYoxla();
header('Content-Type: application/json; charset=utf-8');

$action = $_GET['action'] ?? '';

if ($action === 'rayonlar') {
    $bid = (int)($_GET['bolge_id'] ?? 0);
    $stmt = $pdo->prepare("SELECT id, ad FROM ap_rayonlar WHERE bolge_id=? ORDER BY ad");
    $stmt->execute([$bid]);
    echo json_encode($stmt->fetchAll());
}
