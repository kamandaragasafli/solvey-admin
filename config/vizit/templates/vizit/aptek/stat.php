<?php
require_once __DIR__.'/includes/config.php';
girisYoxla();
rolYoxla(['menecer','div_rehber','rehber']);
$pageTitle='Statistika';
$u=cari();

$fb  = (int)($_GET['bolge_id'] ?? ($u['rol']!=='rehber' ? $u['bolge_id'] : 0));
$ft1 = $_GET['tarix_bas'] ?? date('Y-m-01');
$ft2 = $_GET['tarix_son'] ?? date('Y-m-d');

if ($u['rol']==='rehber'){
    $bolgeler=$pdo->query("SELECT * FROM ap_bolgeler ORDER BY ad")->fetchAll();
} else {
    $s=$pdo->prepare("SELECT * FROM ap_bolgeler WHERE id=?");
    $s->execute([$u['bolge_id']]); $bolgeler=$s->fetchAll();
}

// Nümayəndə üzrə
$numStat=[];
if ($fb){
    $s=$pdo->prepare("
        SELECT i.ad,COUNT(v.id) AS c,
               GROUP_CONCAT(DISTINCT r.ad ORDER BY r.ad SEPARATOR ', ') AS rayonlar
        FROM ap_vizitler v
        JOIN ap_istifadeciler i ON i.id=v.istifadeci_id
        JOIN ap_rayonlar r ON r.id=v.rayon_id
        WHERE v.bolge_id=? AND v.tarix BETWEEN ? AND ?
        GROUP BY i.id ORDER BY c DESC");
    $s->execute([$fb,$ft1,$ft2]); $numStat=$s->fetchAll();
}

// Rayon üzrə
$rayonStat=[];
if ($fb){
    $s=$pdo->prepare("
        SELECT r.ad,COUNT(v.id) AS c
        FROM ap_vizitler v JOIN ap_rayonlar r ON r.id=v.rayon_id
        WHERE v.bolge_id=? AND v.tarix BETWEEN ? AND ?
        GROUP BY r.id ORDER BY c DESC");
    $s->execute([$fb,$ft1,$ft2]); $rayonStat=$s->fetchAll();
}

// Top apteklər
$aptekStat=[];
if ($fb){
    $s=$pdo->prepare("
        SELECT aptek_ad,COUNT(*) AS c
        FROM ap_vizitler
        WHERE bolge_id=? AND tarix BETWEEN ? AND ?
        GROUP BY aptek_ad ORDER BY c DESC LIMIT 10");
    $s->execute([$fb,$ft1,$ft2]); $aptekStat=$s->fetchAll();
}

include __DIR__.'/includes/header.php';
?>

<div class="card no-print">
  <div class="card-title"><span class="ico">🔍</span> Filtr</div>
  <form method="GET">
    <div class="field">
      <label>Bölgə</label>
      <select name="bolge_id" <?=$u['rol']!=='rehber'?'disabled':''?>>
        <option value="">Seçin...</option>
        <?php foreach($bolgeler as $b):?><option value="<?=$b['id']?>" <?=$fb==$b['id']?'selected':''?>><?=htmlspecialchars($b['ad'])?></option><?php endforeach;?>
      </select>
      <?php if($u['rol']!=='rehber'):?><input type="hidden" name="bolge_id" value="<?=$u['bolge_id']?>"><?php endif;?>
    </div>
    <div class="g2">
      <div class="field"><label>Başlanğıc</label><input type="date" name="tarix_bas" value="<?=htmlspecialchars($ft1)?>"></div>
      <div class="field"><label>Son</label><input type="date" name="tarix_son" value="<?=htmlspecialchars($ft2)?>"></div>
    </div>
    <div style="display:flex;gap:8px">
      <button type="submit" class="btn-outline btn-primary" style="flex:1">🔍 Göstər</button>
      <a href="stat.php" class="btn-outline" style="flex:1;text-align:center">↺ Sıfırla</a>
    </div>
  </form>
</div>

<?php if (!$fb): ?>
<div class="card"><div class="alert alert-info">ℹ️ Statistikanı görmək üçün bölgə seçin.</div></div>
<?php elseif (empty($numStat)): ?>
<div class="card"><div class="empty"><div class="empty-ico">📭</div><p>Bu dövr üçün məlumat yoxdur.</p></div></div>
<?php else: ?>

<div class="card">
  <div class="card-title"><span class="ico">👤</span> Nümayəndə üzrə vizit</div>
  <?php foreach($numStat as $i=>$n):?>
  <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--brd)">
    <div style="width:28px;height:28px;background:var(--pr);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0"><?=$i+1?></div>
    <div style="flex:1">
      <div style="font-weight:700"><?=htmlspecialchars($n['ad'])?></div>
      <div style="font-size:12px;color:var(--muted)"><?=htmlspecialchars($n['rayonlar'])?></div>
    </div>
    <div style="font-size:28px;font-weight:900;color:var(--pr)"><?=$n['c']?></div>
  </div>
  <?php endforeach;?>
</div>

<div class="card">
  <div class="card-title"><span class="ico">📍</span> Rayon üzrə vizit</div>
  <?php foreach($rayonStat as $r):?>
  <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--brd)">
    <span><?=htmlspecialchars($r['ad'])?></span>
    <strong style="color:var(--pr)"><?=$r['c']?></strong>
  </div>
  <?php endforeach;?>
</div>

<?php if($aptekStat):?>
<div class="card">
  <div class="card-title"><span class="ico">🏪</span> Ən çox ziyarət olunan apteklər</div>
  <?php foreach($aptekStat as $i=>$a):?>
  <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--brd)">
    <span style="color:var(--muted);font-size:13px;width:20px"><?=$i+1?>.</span>
    <span style="flex:1;font-weight:600"><?=htmlspecialchars($a['aptek_ad'])?></span>
    <strong style="color:var(--teal2)"><?=$a['c']?></strong>
  </div>
  <?php endforeach;?>
</div>
<?php endif;?>

<?php endif;?>

<?php include __DIR__.'/includes/footer.php';?>
