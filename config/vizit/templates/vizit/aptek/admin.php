<?php
require_once __DIR__.'/includes/config.php';
girisYoxla();
rolYoxla(['rehber']);
$pageTitle='Admin';
$msg='';

if ($_SERVER['REQUEST_METHOD']==='POST' && isset($_POST['add_user'])){
    $login=$_POST['login']??''; $sifre=$_POST['sifre']??'';
    $ad=$_POST['ad']??''; $rol=$_POST['rol']??'numayende';
    $bid=(int)($_POST['bolge_id']??0)?:null;
    if ($login&&$sifre&&$ad){
        try{
            $pdo->prepare("INSERT INTO ap_istifadeciler (login,sifre,ad,rol,bolge_id) VALUES (?,MD5(?),?,?,?)")
                ->execute([$login,$sifre,$ad,$rol,$bid]);
            $msg='ok';
        } catch(Exception $e){$msg='err';}
    }
}
if (isset($_GET['del'])){
    $pdo->prepare("DELETE FROM ap_istifadeciler WHERE id=?")->execute([(int)$_GET['del']]);
    header('Location: admin.php?m=del'); exit;
}

$istifadeciler=$pdo->query("SELECT i.*,b.ad AS bolge FROM ap_istifadeciler i LEFT JOIN ap_bolgeler b ON b.id=i.bolge_id ORDER BY i.rol,i.ad")->fetchAll();
$bolgeler=$pdo->query("SELECT * FROM ap_bolgeler ORDER BY ad")->fetchAll();

include __DIR__.'/includes/header.php';
?>
<?php if($msg==='ok'):?><div class="alert alert-ok">✅ İstifadəçi əlavə edildi.</div><?php endif;?>
<?php if($msg==='err'):?><div class="alert alert-err">❌ Login artıq mövcuddur.</div><?php endif;?>
<?php if(isset($_GET['m'])&&$_GET['m']==='del'):?><div class="alert alert-ok">✅ Silindi.</div><?php endif;?>

<div class="card">
  <div class="card-title"><span class="ico">➕</span> Yeni İstifadəçi</div>
  <form method="POST" autocomplete="off">
    <div class="field"><label>Login</label><input type="text" name="login" required placeholder="İstifadəçi adı"></div>
    <div class="field"><label>Şifrə</label><input type="text" name="sifre" required placeholder="Şifrə"></div>
    <div class="field"><label>Ad</label><input type="text" name="ad" required placeholder="Tam adı"></div>
    <div class="field">
      <label>Rol</label>
      <select name="rol">
        <option value="numayende">Tibbi Nümayəndə</option>
        <option value="menecer">Menecer</option>
        <option value="div_rehber">Diviziya Rəhbəri</option>
        <option value="rehber">Rəhbər</option>
      </select>
    </div>
    <div class="field">
      <label>Bölgə</label>
      <select name="bolge_id">
        <option value="">Seçin...</option>
        <?php foreach($bolgeler as $b):?><option value="<?=$b['id']?>"><?=htmlspecialchars($b['ad'])?></option><?php endforeach;?>
      </select>
    </div>
    <button type="submit" name="add_user" class="btn-outline btn-primary" style="width:100%;padding:13px">➕ Əlavə et</button>
  </form>
</div>

<div class="card">
  <div class="card-title"><span class="ico">👥</span> İstifadəçilər</div>
  <?php foreach($istifadeciler as $u2):?>
  <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--brd)">
    <div style="flex:1">
      <div style="font-weight:700"><?=htmlspecialchars($u2['ad'])?></div>
      <div style="font-size:12px;color:var(--muted)"><?=htmlspecialchars($u2['login'])?> · <?=htmlspecialchars($u2['bolge']??'—')?></div>
    </div>
    <span class="rbadge rbadge-<?=$u2['rol']?>"><?=rolAd($u2['rol'])?></span>
    <a href="?del=<?=$u2['id']?>" onclick="return confirm('Silinsin?')" style="color:var(--red);font-size:18px;text-decoration:none">🗑</a>
  </div>
  <?php endforeach;?>
</div>

<?php include __DIR__.'/includes/footer.php';?>
