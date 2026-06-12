<?php
require_once __DIR__.'/includes/config.php';
girisYoxla();
$pageTitle='Yeni Vizit';
$u=cari();

// ── VİZİTİ SAXLA ────────────────────────────────────────────────
$msg='';
if ($_SERVER['REQUEST_METHOD']==='POST' && isset($_POST['vizit_saxla'])){
    $rayon_id   = (int)($_POST['rayon_id']??0);
    $bolge_id   = (int)($_POST['bolge_id']??0);
    $aptek_ad   = trim($_POST['aptek_ad']??'');
    $aptek_nom  = trim($_POST['aptek_nomre']??'');
    $ref_vez    = $_POST['ref_veziyyeti']??'';
    $aptek_iscisi= trim($_POST['aptek_iscisi']??'');
    $qeyd       = trim($_POST['qeyd']??'');
    $tarix      = date('Y-m-d');
    $vaxt       = date('H:i');

    // Preparat məlumatları
    $sorusulub_ids= array_map('intval', $_POST['sorusulub']??[]);
    $satilib_ids  = array_map('intval', $_POST['satilib']??[]);
    $yoxdur_ids   = array_map('intval', $_POST['yoxdur']??[]);

    $refler = ['Ayrıca rəfdə','Fərqli rəflərdə'];

    if ($rayon_id && $bolge_id && $aptek_ad && in_array($ref_vez,$refler)){
        $s=$pdo->prepare("INSERT INTO ap_vizitler
            (istifadeci_id,rayon_id,bolge_id,aptek_ad,aptek_nomre,ref_veziyyeti,aptek_iscisi,qeyd,tarix,vaxt)
            VALUES (?,?,?,?,?,?,?,?,?,?)");
        $s->execute([$u['id'],$rayon_id,$bolge_id,$aptek_ad,$aptek_nom,$ref_vez,$aptek_iscisi,$qeyd,$tarix,$vaxt]);
        $vid=$pdo->lastInsertId();

        // Bütün preparat ID-lərini topla
        $all_ids = array_unique(array_merge($sorusulub_ids,$satilib_ids,$yoxdur_ids));
        if($all_ids){
            $sp=$pdo->prepare("INSERT INTO ap_vizit_preparatlar
                (vizit_id,preparat_id,sorusulub,satilıb,movcuddur) VALUES (?,?,?,?,?)
                ON DUPLICATE KEY UPDATE sorusulub=VALUES(sorusulub),satilıb=VALUES(satilıb),movcuddur=VALUES(movcuddur)");
            foreach($all_ids as $pid){
                $sp->execute([
                    $vid, $pid,
                    in_array($pid,$sorusulub_ids)?1:0,
                    in_array($pid,$satilib_ids)?1:0,
                    in_array($pid,$yoxdur_ids)?0:1  // yoxdur seçilməyibsə → mövcuddur
                ]);
            }
        }
        $msg='ok';
    } else {
        $msg='err';
    }
}

// ── DATA ────────────────────────────────────────────────────────
// Bölgə siyahısı — rola görə
if ($u['rol']==='numayende'||$u['rol']==='menecer'||$u['rol']==='div_rehber'){
    $bolgeler=$pdo->prepare("SELECT * FROM ap_bolgeler WHERE id=?");
    $bolgeler->execute([$u['bolge_id']]);
    $bolgeler=$bolgeler->fetchAll();
} else {
    $bolgeler=$pdo->query("SELECT * FROM ap_bolgeler ORDER BY ad")->fetchAll();
}

$preparatlar=$pdo->query("SELECT * FROM ap_preparatlar ORDER BY sira")->fetchAll();

// Bugünkü vizitlər
$bugun=date('Y-m-d');
$wh="v.tarix=?"; $wp=[$bugun];
if ($u['rol']==='numayende'){$wh.=" AND v.istifadeci_id=?";$wp[]=$u['id'];}
elseif (in_array($u['rol'],['menecer','div_rehber'])){$wh.=" AND v.bolge_id=?";$wp[]=$u['bolge_id'];}

$sq=$pdo->prepare("
    SELECT v.*,r.ad AS rayon,b.ad AS bolge, i.ad AS numayende_ad
    FROM ap_vizitler v
    JOIN ap_rayonlar r ON r.id=v.rayon_id
    JOIN ap_bolgeler b ON b.id=v.bolge_id
    JOIN ap_istifadeciler i ON i.id=v.istifadeci_id
    WHERE $wh ORDER BY v.id DESC");
$sq->execute($wp);
$bugunVizitler=$sq->fetchAll();

// Hər vizit üçün preparatları çək
$vizitPreps=[];
if ($bugunVizitler){
    $vids=array_column($bugunVizitler,'id');
    $in=implode(',',array_fill(0,count($vids),'?'));
    $sp=$pdo->prepare("SELECT vp.*,p.ad FROM ap_vizit_preparatlar vp
        JOIN ap_preparatlar p ON p.id=vp.preparat_id WHERE vp.vizit_id IN ($in)");
    $sp->execute($vids);
    foreach($sp->fetchAll() as $row){
        $vizitPreps[$row['vizit_id']][]=$row;
    }
}

include __DIR__.'/includes/header.php';
?>

<?php if($msg==='ok'):?>
<div class="alert alert-ok">✅ Aptek viziti uğurla qeydə alındı!</div>
<?php elseif($msg==='err'):?>
<div class="alert alert-err">❌ Xəta: Rayon, aptek adı və rəf vəziyyəti mütləqdir.</div>
<?php endif;?>

<div class="steps">
  <div class="step act">1 Məkan</div>
  <div class="step">2 Dərmanlar</div>
  <div class="step">3 Satış & Mövcud</div>
  <div class="step">4 Rəf & Bağla</div>
</div>

<form method="POST" id="vizit-form" autocomplete="off">

<!-- STEP 1: Rayon + Aptek -->
<div class="card" id="s1">
  <div class="card-title"><span class="ico">📍</span> Rayon və Aptek</div>
  <div class="field">
    <label>Bölgə</label>
    <select name="bolge_id" id="bolge_id" <?=count($bolgeler)===1?'':'';?>>
      <option value="">Seçin...</option>
      <?php foreach($bolgeler as $b):?>
      <option value="<?=$b['id']?>" <?=count($bolgeler)===1?'selected':'';?>><?=htmlspecialchars($b['ad'])?></option>
      <?php endforeach;?>
    </select>
  </div>
  <div class="field">
    <label>Rayon</label>
    <select name="rayon_id" id="rayon_id" required disabled>
      <option value="">Əvvəlcə bölgə...</option>
    </select>
  </div>
  <div class="field">
    <label>Aptekin adı</label>
    <input type="text" name="aptek_ad" id="aptek_ad" placeholder="Aptekin tam adı" required>
  </div>
  <div class="field">
    <label>Aptekin nömrəsi (ixtiyari)</label>
    <input type="text" name="aptek_nomre" placeholder="№ 12 və ya filial adı">
  </div>
</div>

<!-- STEP 2: Soruşulan dərmanlar -->
<div class="card" id="s2">
  <div class="card-title"><span class="ico">🔍</span> Soruşulan dərmanlar</div>
  <div style="display:flex;gap:8px;margin-bottom:12px;">
    <button type="button" class="btn-outline btn-primary" id="sorusulub-all" style="font-size:13px;padding:9px 14px;">✅ Bütün siyahı</button>
    <button type="button" class="btn-outline" id="sorusulub-clear" style="font-size:13px;padding:9px 14px;">❌ Sıfırla</button>
  </div>
  <div class="chip-grid" id="sorusulub-grid">
    <?php foreach($preparatlar as $p):?>
    <div class="chip" data-id="<?=$p['id']?>" data-group="sorusulub">
      <span class="chip-ico">○</span><?=htmlspecialchars($p['ad'])?>
      <input type="checkbox" name="sorusulub[]" value="<?=$p['id']?>" style="display:none">
    </div>
    <?php endforeach;?>
  </div>
</div>

<!-- STEP 3: Satış vəziyyəti -->
<div class="card" id="s3">
  <div class="card-title"><span class="ico">💰</span> Satışın vəziyyəti</div>
  <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
    <button type="button" class="btn-outline" id="satis-yox-btn" style="font-size:13px;padding:9px 14px;border-color:#e74c3c;color:#e74c3c;">
      🚫 Satış olmayıb
    </button>
    <button type="button" class="btn-outline btn-success" id="satis-all-btn" style="font-size:13px;padding:9px 14px;">
      ✅ Hamısı satılıb
    </button>
    <button type="button" class="btn-outline" id="satis-clear" style="font-size:13px;padding:9px 14px;">↺ Sıfırla</button>
  </div>
  <p style="font-size:12px;color:var(--muted);margin-bottom:10px;">Yalnız satılan preparatları seçin:</p>
  <div class="chip-grid" id="satilib-grid">
    <?php foreach($preparatlar as $p):?>
    <div class="chip" data-id="<?=$p['id']?>" data-group="satilib">
      <span class="chip-ico">○</span><?=htmlspecialchars($p['ad'])?>
      <input type="checkbox" name="satilib[]" value="<?=$p['id']?>" style="display:none">
    </div>
    <?php endforeach;?>
  </div>
</div>

<!-- STEP 4: Mövcudluq -->
<div class="card" id="s4">
  <div class="card-title"><span class="ico">📦</span> Aptekdəki mövcudluq</div>
  <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
    <button type="button" class="btn-outline btn-success" id="movcud-all-btn" style="font-size:13px;padding:9px 14px;">
      ✅ Hamısı var
    </button>
    <button type="button" class="btn-outline" id="movcud-clear" style="font-size:13px;padding:9px 14px;">↺ Sıfırla</button>
  </div>
  <p style="font-size:12px;color:var(--muted);margin-bottom:10px;">Olmayan preparatları seçin (qırmızı = yoxdur):</p>
  <div class="chip-grid" id="yoxdur-grid">
    <?php foreach($preparatlar as $p):?>
    <div class="chip" data-id="<?=$p['id']?>" data-group="yoxdur">
      <span class="chip-ico">○</span><?=htmlspecialchars($p['ad'])?>
      <input type="checkbox" name="yoxdur[]" value="<?=$p['id']?>" style="display:none">
    </div>
    <?php endforeach;?>
  </div>
</div>

<!-- STEP 5: Rəf + İşçi + Bağla -->
<div class="card" id="s5">
  <div class="card-title"><span class="ico">🏪</span> Rəf vəziyyəti</div>
  <input type="hidden" name="ref_veziyyeti" id="ref_val">
  <div class="ref-btns">
    <button type="button" class="ref-btn" data-val="Ayrıca rəfdə" id="ref1">
      🗂️ Ayrıca rəfdə
    </button>
    <button type="button" class="ref-btn" data-val="Fərqli rəflərdə" id="ref2">
      📚 Fərqli rəflərdə
    </button>
  </div>

  <hr class="divider" style="margin:16px 0">

  <div class="field">
    <label>Aptek işçisinin adı</label>
    <input type="text" name="aptek_iscisi" placeholder="Əczacı / işçinin adı">
  </div>
  <div class="field">
    <label>Qeyd (ixtiyari)</label>
    <textarea name="qeyd" placeholder="Əlavə məlumat..."></textarea>
  </div>

  <button type="submit" name="vizit_saxla" class="btn-submit" id="submit-btn">
    🔒 Viziti Bağla
  </button>
</div>

</form>

<!-- BUGÜNKÜ VİZİTLƏR -->
<div class="card" style="margin-top:24px">
  <div class="card-title" style="justify-content:space-between">
    <span><span class="ico">📋</span> Bu gün — <?=count($bugunVizitler)?> vizit</span>
    <?php if(count($bugunVizitler)>0):?>
    <a href="export.php?tarix=<?=date('Y-m-d')?><?=($u['bolge_id']?'&bolge_id='.$u['bolge_id']:'')?>" class="btn-outline btn-success no-print" style="font-size:12px;padding:6px 12px;">📥 Excel</a>
    <?php endif;?>
  </div>

  <?php if(empty($bugunVizitler)):?>
  <div class="empty"><div class="empty-ico">📭</div><p>Bu gün hələ vizit yoxdur.</p></div>
  <?php else: foreach($bugunVizitler as $i=>$v):
    $preps=$vizitPreps[$v['id']]??[];
    $sorusulub_list=array_filter($preps,fn($x)=>$x['sorusulub']);
    $satilib_list=array_filter($preps,fn($x)=>$x['satilıb']);
    $yoxdur_list=array_filter($preps,fn($x)=>!$x['movcuddur']);
  ?>
  <div class="vcard">
    <div class="vcard-top">
      <div class="vcard-aptek"><?=htmlspecialchars($v['aptek_ad'])?><?=$v['aptek_nomre']?' <small style="font-weight:500;font-size:13px;color:var(--muted);">'.htmlspecialchars($v['aptek_nomre']).'</small>':''?></div>
      <div class="vcard-time">🕐 <?=substr($v['vaxt'],0,5)?></div>
    </div>
    <div class="vcard-meta">
      <span class="tag tag-rayon">📍 <?=htmlspecialchars($v['rayon'])?></span>
      <span class="tag tag-ref">🗂️ <?=htmlspecialchars($v['ref_veziyyeti'])?></span>
      <?php if($u['rol']!=='numayende'):?><span class="tag tag-user">👤 <?=htmlspecialchars($v['numayende_ad'])?></span><?php endif;?>
    </div>
    <?php if($v['aptek_iscisi']):?>
    <div style="font-size:13px;color:var(--muted);margin-top:6px;">👩‍⚕️ <?=htmlspecialchars($v['aptek_iscisi'])?></div>
    <?php endif;?>
    <div class="vcard-prep">
      <?php if($sorusulub_list):?>
      <div class="prep-group"><span>Soruşulan:</span>
        <div class="prep-pills"><?php foreach($sorusulub_list as $p):?><span class="pill pill-sorusulub"><?=htmlspecialchars($p['ad'])?></span><?php endforeach;?></div>
      </div><?php endif;?>
      <?php if($satilib_list):?>
      <div class="prep-group" style="margin-top:4px"><span>Satılıb:</span>
        <div class="prep-pills"><?php foreach($satilib_list as $p):?><span class="pill pill-satilib"><?=htmlspecialchars($p['ad'])?></span><?php endforeach;?></div>
      </div><?php endif;?>
      <?php if($yoxdur_list):?>
      <div class="prep-group" style="margin-top:4px"><span>Yoxdur:</span>
        <div class="prep-pills"><?php foreach($yoxdur_list as $p):?><span class="pill pill-yoxdur"><?=htmlspecialchars($p['ad'])?></span><?php endforeach;?></div>
      </div><?php endif;?>
    </div>
  </div>
  <?php endforeach; endif;?>
</div>

<?php include __DIR__.'/includes/footer.php';?>
