<?php
require_once __DIR__.'/includes/config.php';
girisYoxla();
$pageTitle='Hesabat';
$u=cari();

$fb  = (int)($_GET['bolge_id'] ?? ($u['rol']!=='rehber' ? $u['bolge_id'] : 0));
$fr  = (int)($_GET['rayon_id'] ?? 0);
$ft1 = $_GET['tarix_bas'] ?? date('Y-m-d');
$ft2 = $_GET['tarix_son'] ?? date('Y-m-d');

// Bölgə siyahısı
if ($u['rol']==='rehber'){
    $bolgeler=$pdo->query("SELECT * FROM ap_bolgeler ORDER BY ad")->fetchAll();
} else {
    $s=$pdo->prepare("SELECT * FROM ap_bolgeler WHERE id=?");
    $s->execute([$u['bolge_id']]);
    $bolgeler=$s->fetchAll();
}
$rayonlar=[];
if ($fb){
    $s=$pdo->prepare("SELECT * FROM ap_rayonlar WHERE bolge_id=? ORDER BY ad");
    $s->execute([$fb]); $rayonlar=$s->fetchAll();
}

$wh=["v.tarix BETWEEN ? AND ?"]; $wp=[$ft1,$ft2];
if ($u['rol']==='numayende'){$wh[]="v.istifadeci_id=?";$wp[]=$u['id'];}
elseif ($u['rol']!=='rehber'){$wh[]="v.bolge_id=?";$wp[]=$u['bolge_id'];}
if ($fb) {$wh[]="v.bolge_id=?";$wp[]=$fb;}
if ($fr) {$wh[]="v.rayon_id=?";$wp[]=$fr;}
$whSQL=implode(' AND ',$wh);

$sq=$pdo->prepare("
    SELECT v.*,r.ad AS rayon,b.ad AS bolge,i.ad AS numayende_ad
    FROM ap_vizitler v
    JOIN ap_rayonlar r ON r.id=v.rayon_id
    JOIN ap_bolgeler b ON b.id=v.bolge_id
    JOIN ap_istifadeciler i ON i.id=v.istifadeci_id
    WHERE $whSQL ORDER BY v.tarix DESC,v.vaxt DESC");
$sq->execute($wp); $vizitler=$sq->fetchAll();

// Hər vizit üçün preparatlar
$vizitPreps=[];
if ($vizitler){
    $vids=array_column($vizitler,'id');
    $in=implode(',',array_fill(0,count($vids),'?'));
    $sp=$pdo->prepare("SELECT vp.*,p.ad FROM ap_vizit_preparatlar vp
        JOIN ap_preparatlar p ON p.id=vp.preparat_id WHERE vp.vizit_id IN ($in)");
    $sp->execute($vids);
    foreach($sp->fetchAll() as $row) $vizitPreps[$row['vizit_id']][]=$row;
}

$qParams=http_build_query($_GET);
include __DIR__.'/includes/header.php';
?>

<div class="card no-print">
  <div class="card-title"><span class="ico">🔍</span> Filtr</div>
  <form method="GET">
    <?php if ($u['rol']==='rehber'):?>
    <div class="field">
      <label>Bölgə</label>
      <select name="bolge_id" id="f_bolge">
        <option value="">Hamısı</option>
        <?php foreach($bolgeler as $b):?><option value="<?=$b['id']?>" <?=$fb==$b['id']?'selected':''?>><?=htmlspecialchars($b['ad'])?></option><?php endforeach;?>
      </select>
    </div>
    <?php else:?>
    <input type="hidden" name="bolge_id" value="<?=$u['bolge_id']?>">
    <?php endif;?>
    <div class="field">
      <label>Rayon</label>
      <select name="rayon_id" id="f_rayon">
        <option value="">Hamısı</option>
        <?php foreach($rayonlar as $r):?><option value="<?=$r['id']?>" <?=$fr==$r['id']?'selected':''?>><?=htmlspecialchars($r['ad'])?></option><?php endforeach;?>
      </select>
    </div>
    <div class="g2">
      <div class="field"><label>Başlanğıc</label><input type="date" name="tarix_bas" value="<?=htmlspecialchars($ft1)?>"></div>
      <div class="field"><label>Son</label><input type="date" name="tarix_son" value="<?=htmlspecialchars($ft2)?>"></div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
      <button type="submit" class="btn-outline btn-primary" style="flex:1">🔍 Filtrle</button>
      <a href="hesabat.php" class="btn-outline" style="flex:1;text-align:center">↺ Sıfırla</a>
      <a href="export.php?<?=htmlspecialchars($qParams)?>" class="btn-outline btn-success" style="flex:1;text-align:center">📥 Excel</a>
    </div>
  </form>
</div>

<div class="stat-grid">
  <div class="stat-box"><div class="stat-num"><?=count($vizitler)?></div><div class="stat-lbl">Vizit</div></div>
  <div class="stat-box"><div class="stat-num"><?=count(array_unique(array_column($vizitler,'aptek_ad')))?></div><div class="stat-lbl">Unikal Aptek</div></div>
</div>

<?php if(empty($vizitler)):?>
<div class="card"><div class="empty"><div class="empty-ico">🔍</div><p>Nəticə tapılmadı.</p></div></div>
<?php else: foreach($vizitler as $v):
  $preps=$vizitPreps[$v['id']]??[];
  $sorusulub=array_filter($preps,fn($x)=>$x['sorusulub']);
  $satilib=array_filter($preps,fn($x)=>$x['satilıb']);
  $yoxdur=array_filter($preps,fn($x)=>!$x['movcuddur']);
?>
<div class="vcard">
  <div class="vcard-top">
    <div>
      <div class="vcard-aptek"><?=htmlspecialchars($v['aptek_ad'])?><?=$v['aptek_nomre']?' <small style="font-size:12px;color:var(--muted)">'.htmlspecialchars($v['aptek_nomre']).'</small>':''?></div>
      <div style="font-size:12px;color:var(--muted);margin-top:2px">📅 <?=date('d.m.Y',strtotime($v['tarix']))?></div>
    </div>
    <div class="vcard-time">🕐 <?=substr($v['vaxt'],0,5)?></div>
  </div>
  <div class="vcard-meta">
    <span class="tag tag-rayon">📍 <?=htmlspecialchars($v['rayon'])?></span>
    <span class="tag tag-ref">🗂️ <?=htmlspecialchars($v['ref_veziyyeti'])?></span>
    <?php if($u['rol']!=='numayende'):?><span class="tag tag-user">👤 <?=htmlspecialchars($v['numayende_ad'])?></span><?php endif;?>
  </div>
  <?php if($v['aptek_iscisi']):?><div style="font-size:13px;color:var(--muted);margin-top:6px">👩‍⚕️ <?=htmlspecialchars($v['aptek_iscisi'])?></div><?php endif;?>
  <div class="vcard-prep">
    <?php if($sorusulub):?><div class="prep-group"><span>Soruşulan:</span><div class="prep-pills"><?php foreach($sorusulub as $p):?><span class="pill pill-sorusulub"><?=htmlspecialchars($p['ad'])?></span><?php endforeach;?></div></div><?php endif;?>
    <?php if($satilib):?><div class="prep-group" style="margin-top:4px"><span>Satılıb:</span><div class="prep-pills"><?php foreach($satilib as $p):?><span class="pill pill-satilib"><?=htmlspecialchars($p['ad'])?></span><?php endforeach;?></div></div><?php endif;?>
    <?php if($yoxdur):?><div class="prep-group" style="margin-top:4px"><span>Yoxdur:</span><div class="prep-pills"><?php foreach($yoxdur as $p):?><span class="pill pill-yoxdur"><?=htmlspecialchars($p['ad'])?></span><?php endforeach;?></div></div><?php endif;?>
  </div>
  <?php if($v['qeyd']):?><div style="font-size:13px;color:#555;margin-top:6px;padding-top:6px;border-top:1px solid var(--brd)">📝 <?=htmlspecialchars($v['qeyd'])?></div><?php endif;?>
</div>
<?php endforeach; endif;?>

<?php include __DIR__.'/includes/footer.php';?>
