document.addEventListener('DOMContentLoaded', function () {

    // ── BÖLGƏ → RAYON → HƏKİM kaskadı ──────────────────────────
    const bolgeSelect  = document.getElementById('bolge_id');
    const rayonSelect  = document.getElementById('rayon_id');
    const hekimSelect  = document.getElementById('hekim_id');
    const hekimInfo    = document.getElementById('hekim-info');

    if (bolgeSelect && rayonSelect) {
        // Əgər bölgə artıq seçilibsə (1 bölgəli nümayəndə) — rayonları yüklə
        if (bolgeSelect.value) loadRayonlar(bolgeSelect.value);

        bolgeSelect.addEventListener('change', function () {
            resetSelect(rayonSelect, 'Əvvəlcə bölgə...');
            resetSelect(hekimSelect, 'Əvvəlcə rayon...');
            if (hekimInfo) hekimInfo.classList.add('hidden');
            if (!this.value) return;
            loadRayonlar(this.value);
        });
    }

    if (rayonSelect && hekimSelect) {
        rayonSelect.addEventListener('change', function () {
            resetSelect(hekimSelect, 'Həkim seçin...');
            if (hekimInfo) hekimInfo.classList.add('hidden');
            if (!this.value) return;
            loadHekimler(this.value);
        });
    }

    if (hekimSelect) {
        hekimSelect.addEventListener('change', function () {
            if (!this.value || !hekimInfo) return;
            const opt = this.options[this.selectedIndex];
            const ixtisas  = opt.dataset.ixtisas  || '';
            const ixtKod   = opt.dataset.ixtKod   || '';
            const kat      = opt.dataset.kat       || '';
            let html = '';
            if (ixtKod)  html += `<span>🩺 <strong>${escHtml(ixtKod)}</strong> — ${escHtml(ixtisas)}</span>`;
            if (kat)     html += `<span>🏷️ Kateqoriya: <strong>${escHtml(kat)}</strong></span>`;
            if (html) { hekimInfo.innerHTML = html; hekimInfo.classList.remove('hidden'); }
            else        hekimInfo.classList.add('hidden');
        });
    }

    function loadRayonlar(bolgeId) {
        rayonSelect.disabled = true;
        fetch(`ajax.php?action=rayonlar&bolge_id=${bolgeId}`)
            .then(r => r.json())
            .then(data => {
                rayonSelect.innerHTML = '<option value="">Rayon seçin...</option>';
                data.forEach(r => {
                    const opt = new Option(r.ad, r.id);
                    rayonSelect.add(opt);
                });
                rayonSelect.disabled = false;
            });
    }

    function loadHekimler(rayonId) {
        hekimSelect.disabled = true;
        fetch(`ajax.php?action=hekimler&rayon_id=${rayonId}`)
            .then(r => r.json())
            .then(data => {
                hekimSelect.innerHTML = '<option value="">Həkim seçin...</option>';
                data.forEach(h => {
                    const opt = new Option(h.ad_soyad, h.id);
                    opt.dataset.ixtisas = h.ixtisas   || '';
                    opt.dataset.ixtKod  = h.ixtisas_kod || '';
                    opt.dataset.kat     = h.kateqoriya || '';
                    hekimSelect.add(opt);
                });
                hekimSelect.disabled = false;
            });
    }

    function resetSelect(sel, placeholder) {
        sel.innerHTML = `<option value="">${placeholder}</option>`;
        sel.disabled = true;
    }

    // ── MÜNASIBƏT ────────────────────────────────────────────────
    const munasibatBtns  = document.querySelectorAll('.munasibat-btn');
    const munasibatInput = document.getElementById('munasibat_val');
    const preparatSection = document.getElementById('preparat-section');

    munasibatBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            munasibatBtns.forEach(b => b.classList.remove('selected'));
            this.classList.add('selected');
            if (munasibatInput) munasibatInput.value = this.dataset.val;
            if (preparatSection) preparatSection.classList.remove('hidden');
            preparatSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    // ── PREPARAT SEÇİMİ ──────────────────────────────────────────
    document.querySelectorAll('.preparat-item').forEach(item => {
        item.addEventListener('click', function (e) {
            if (e.target.tagName === 'INPUT') return;
            const cb = this.querySelector('input[type="checkbox"]');
            cb.checked = !cb.checked;
            this.classList.toggle('checked', cb.checked);
        });
        const cb = item.querySelector('input[type="checkbox"]');
        if (cb) cb.addEventListener('change', function () {
            item.classList.toggle('checked', this.checked);
        });
    });

    // ── HAMISI SEÇ / SIFIRLA ─────────────────────────────────────
    document.getElementById('select-all-prep')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="preparatlar[]"]').forEach(cb => {
            cb.checked = true;
            cb.closest('.preparat-item')?.classList.add('checked');
        });
    });
    document.getElementById('clear-all-prep')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="preparatlar[]"]').forEach(cb => {
            cb.checked = false;
            cb.closest('.preparat-item')?.classList.remove('checked');
        });
    });

    // ── VİZİTİ BAĞLA — VALİDASİYA ───────────────────────────────
    document.querySelector('.vizit-bagla-btn')?.addEventListener('click', function (e) {
        const hekim     = document.getElementById('hekim_id')?.value;
        const munasibat = document.getElementById('munasibat_val')?.value;
        const checked   = document.querySelectorAll('input[name="preparatlar[]"]:checked');
        if (!hekim)            { showAlert('Zəhmət olmasa həkim seçin!', 'error');           e.preventDefault(); return; }
        if (!munasibat)        { showAlert('Zəhmət olmasa münasibət növü seçin!', 'error');   e.preventDefault(); return; }
        if (checked.length===0){ showAlert('Zəhmət olmasa ən azı 1 preparat seçin!', 'error'); e.preventDefault(); return; }
    });

    // ── ÇAPP ─────────────────────────────────────────────────────
    document.getElementById('print-btn')?.addEventListener('click', () => window.print());

    // ── HESABATda bölgə → rayon filter ───────────────────────────
    const fBolge = document.getElementById('f_bolge');
    const fRayon = document.getElementById('f_rayon');
    if (fBolge && fRayon) {
        fBolge.addEventListener('change', function () {
            fRayon.innerHTML = '<option value="">Hamısı</option>';
            if (!this.value) return;
            fetch(`ajax.php?action=rayonlar&bolge_id=${this.value}`)
                .then(r => r.json())
                .then(data => {
                    data.forEach(r => fRayon.add(new Option(r.ad, r.id)));
                });
        });
    }

    // ── HELPER ───────────────────────────────────────────────────
    function showAlert(msg, type) {
        let el = document.getElementById('js-alert');
        if (!el) {
            el = document.createElement('div');
            el.id = 'js-alert';
            document.querySelector('.container')?.prepend(el);
        }
        el.className = `alert alert-${type==='error'?'error':'success'}`;
        el.textContent = msg;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => el.remove(), 4000);
    }

    function escHtml(str) {
        return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }
});
