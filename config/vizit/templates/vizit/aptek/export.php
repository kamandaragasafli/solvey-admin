<?php
require_once __DIR__.'/includes/config.php';
girisYoxla();
$u=cari();

$fb  = (int)($_GET['bolge_id'] ?? ($u['rol']!=='rehber' ? $u['bolge_id'] : 0));
$fr  = (int)($_GET['rayon_id'] ?? 0);
$ft1 = $_GET['tarix_bas'] ?? date('Y-m-d');
$ft2 = $_GET['tarix_son'] ?? date('Y-m-d');

$wh=["v.tarix BETWEEN ? AND ?"]; $wp=[$ft1,$ft2];
if ($u['rol']==='numayende'){$wh[]="v.istifadeci_id=?";$wp[]=$u['id'];}
elseif ($u['rol']!=='rehber'){$wh[]="v.bolge_id=?";$wp[]=$u['bolge_id'];}
if ($fb){$wh[]="v.bolge_id=?";$wp[]=$fb;}
if ($fr){$wh[]="v.rayon_id=?";$wp[]=$fr;}
$whSQL=implode(' AND ',$wh);

$sq=$pdo->prepare("
    SELECT v.*,r.ad AS rayon,b.ad AS bolge,i.ad AS numayende_ad
    FROM ap_vizitler v
    JOIN ap_rayonlar r ON r.id=v.rayon_id
    JOIN ap_bolgeler b ON b.id=v.bolge_id
    JOIN ap_istifadeciler i ON i.id=v.istifadeci_id
    WHERE $whSQL ORDER BY v.tarix,v.vaxt");
$sq->execute($wp); $vizitler=$sq->fetchAll();

// Preparatlar
$preparatlar=$pdo->query("SELECT * FROM ap_preparatlar ORDER BY sira")->fetchAll();

// Hər vizit üçün prep datası
$vizitPreps=[];
if ($vizitler){
    $vids=array_column($vizitler,'id');
    $in=implode(',',array_fill(0,count($vids),'?'));
    $sp=$pdo->prepare("SELECT vp.*,p.ad FROM ap_vizit_preparatlar vp
        JOIN ap_preparatlar p ON p.id=vp.preparat_id WHERE vp.vizit_id IN ($in)");
    $sp->execute($vids);
    foreach($sp->fetchAll() as $row) $vizitPreps[$row['vizit_id']][$row['preparat_id']]=$row;
}

$tarixAralig = date('d.m.Y',strtotime($ft1));
if ($ft1!==$ft2) $tarixAralig.=' — '.date('d.m.Y',strtotime($ft2));
$fname='Aptek_Vizit_'.$tarixAralig.'.xls';

header('Content-Type: application/vnd.ms-excel; charset=utf-8');
header('Content-Disposition: attachment; filename="'.str_replace([' ','—'],'_',$fname).'"');
header('Cache-Control: max-age=0');
echo "\xEF\xBB\xBF";
?>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:x="urn:schemas-microsoft-com:office:excel">
<head><meta charset="utf-8">
<style>
body{font-family:Arial,sans-serif;font-size:9pt}
table{border-collapse:collapse;width:100%}
td,th{border:1px solid #999;padding:3px 5px;white-space:nowrap}
.h1 td{font-weight:bold;font-size:12pt;background:#1a5276;color:white;text-align:center}
.h2 td{font-weight:bold;font-size:8pt;background:#1abc9c;color:white;text-align:center}
.h3 td{font-weight:700;background:#2980b9;color:white;font-size:9pt}
.info td{background:#eaf4fb;font-size:9pt}
.num{text-align:center}
.c-sor{background:#f5eef8;color:#6c3483;text-align:center;font-weight:700}
.c-sat{background:#eafaf1;color:#1e8449;text-align:center;font-weight:700}
.c-yox{background:#fdf2f2;color:#922b21;text-align:center;font-weight:700}
tr:nth-child(even) td{background:#f9f9f9}
.h1 td,.h2 td,.h3 td,.info td{background:inherit}
</style>
</head><body>
<table>
  <tr class="h1"><td colspan="<?=7+count($preparatlar)*3?>">SOLVEY PHARMA — APTEK VİZİT BLANKI | <?=htmlspecialchars($tarixAralig)?></td></tr>
  <tr class="info">
    <td colspan="3"><b>Ad-Soyad:</b> <?=htmlspecialchars($u['ad'])?></td>
    <td colspan="2"><b>Bölgə:</b> <?php if($fb){$s=$pdo->prepare("SELECT ad FROM ap_bolgeler WHERE id=?");$s->execute([$fb]);echo htmlspecialchars($s->fetchColumn());}else echo 'Hamısı';?></td>
    <td colspan="<?=2+count($preparatlar)*3?>"><b>Tarix:</b> <?=htmlspecialchars($tarixAralig)?></td>
  </tr>
  <!-- Hazırlıq başlığı -->
  <tr class="h2">
    <td rowspan="2" class="num">#</td>
    <td rowspan="2">Aptekin adı və nömrəsi</td>
    <td rowspan="2">Rayon</td>
    <td rowspan="2">Rəfdəki vəziyyət</td>
    <td rowspan="2">Aptek işçisi</td>
    <td rowspan="2">Vaxt</td>
    <td rowspan="2">Nümayəndə</td>
    <?php foreach($preparatlar as $p):?>
    <td colspan="3" style="text-align:center;font-weight:700"><?=htmlspecialchars($p['ad'])?></td>
    <?php endforeach;?>
  </tr>
  <tr class="h3">
    <?php foreach($preparatlar as $p):?>
    <td style="font-size:8pt">Soruşulub</td>
    <td style="font-size:8pt">Satılıb</td>
    <td style="font-size:8pt">Mövcud</td>
    <?php endforeach;?>
  </tr>
  <?php if(empty($vizitler)):?>
  <tr><td colspan="<?=7+count($preparatlar)*3?>" style="text-align:center;color:#999">Məlumat yoxdur</td></tr>
  <?php else: foreach($vizitler as $i=>$v): $preps=$vizitPreps[$v['id']]??[];?>
  <tr>
    <td class="num"><?=$i+1?></td>
    <td><b><?=htmlspecialchars($v['aptek_ad'])?></b><?=$v['aptek_nomre']?' '.htmlspecialchars($v['aptek_nomre']):''?></td>
    <td><?=htmlspecialchars($v['rayon'])?></td>
    <td><?=htmlspecialchars($v['ref_veziyyeti'])?></td>
    <td><?=htmlspecialchars($v['aptek_iscisi']??'')?></td>
    <td><?=substr($v['vaxt'],0,5)?> <?=date('d.m.y',strtotime($v['tarix']))?></td>
    <td><?=htmlspecialchars($v['numayende_ad'])?></td>
    <?php foreach($preparatlar as $p):
      $pd=$preps[$p['id']]??null;
      $sor=$pd&&$pd['sorusulub'];
      $sat=$pd&&$pd['satilıb'];
      $mev=$pd&&$pd['movcuddur'];
    ?>
    <td class="<?=$sor?'c-sor':''?>"><?=$sor?'✓':''?></td>
    <td class="<?=$sat?'c-sat':''?>"><?=$sat?'✓':''?></td>
    <td class="<?=($pd&&!$mev)?'c-yox':($mev?'c-sat':'')?>"> <?=$pd?($mev?'✓':'✗'):''?></td>
    <?php endforeach;?>
  </tr>
  <?php endforeach;endif;?>
  <tr class="info">
    <td colspan="4" style="padding:8px"><b>Diviziya Rəhbəri:</b> _______________</td>
    <td colspan="<?=3+count($preparatlar)*3?>" style="padding:8px"><b>İdarə heyətinin sədri:</b> _______________</td>
  </tr>
</table>
</body></html>
