// Solvey Pharma — Aptek Vizit JS

document.addEventListener('DOMContentLoaded', () => {

    // ── BÖLGƏ → RAYON kaskadı ────────────────────────────────────
    const bolgeEl  = document.getElementById('bolge_id');
    const rayonEl  = document.getElementById('rayon_id');

    if (bolgeEl && rayonEl) {
        if (bolgeEl.value) loadRayonlar(bolgeEl.value);
        bolgeEl.addEventListener('change', () => {
            resetSel(rayonEl, 'Rayon seçin...');
            if (bolgeEl.value) loadRayonlar(bolgeEl.value);
        });
    }

    function loadRayonlar(bid) {
        rayonEl.disabled = true;
        fetch('ajax.php?action=rayonlar&bolge_id=' + bid)
            .then(r => r.json())
            .then(data => {
                rayonEl.innerHTML = '<option value="">Rayon seçin...</option>';
                data.forEach(r => rayonEl.add(new Option(r.ad, r.id)));
                rayonEl.disabled = false;
            });
    }

    function resetSel(el, placeholder) {
        el.innerHTML = `<option value="">${placeholder}</option>`;
        el.disabled = true;
    }

    // ── STEPS progress ───────────────────────────────────────────
    const steps = document.querySelectorAll('.step');
    const sections = ['s1','s2','s3','s4','s5'].map(id => document.getElementById(id));

    function updateSteps() {
        // s1 tamam: rayon + aptek_ad dolu
        const r = document.getElementById('rayon_id');
        const a = document.getElementById('aptek_ad');
        const s1ok = r && r.value && a && a.value.trim();
        if (steps[0]) steps[0].className = 'step ' + (s1ok ? 'done' : 'act');
        if (steps[1]) steps[1].className = 'step ' + (s1ok ? 'act' : '');
    }
    document.getElementById('rayon_id')?.addEventListener('change', updateSteps);
    document.getElementById('aptek_ad')?.addEventListener('input', updateSteps);

    // ── CHİP toggle (soruşulan / satılan / yoxdur) ───────────────
    const groupColors = {
        sorusulub: 'sel-sorusulub',
        satilib:   'sel-satilib',
        yoxdur:    'sel-yoxdur',
    };

    function initChips(gridId) {
        const grid = document.getElementById(gridId);
        if (!grid) return;
        grid.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const grp  = chip.dataset.group;
                const cls  = groupColors[grp];
                const cb   = chip.querySelector('input[type=checkbox]');
                const on   = chip.classList.contains(cls);
                chip.classList.toggle(cls, !on);
                chip.querySelector('.chip-ico').textContent = on ? '○' : '✓';
                if (cb) cb.checked = !on;
            });
        });
    }
    initChips('sorusulub-grid');
    initChips('satilib-grid');
    initChips('yoxdur-grid');

    // "Bütün siyahı" — soruşulan
    document.getElementById('sorusulub-all')?.addEventListener('click', () => {
        document.querySelectorAll('#sorusulub-grid .chip').forEach(chip => {
            chip.classList.add('sel-sorusulub');
            chip.querySelector('.chip-ico').textContent = '✓';
            const cb = chip.querySelector('input'); if (cb) cb.checked = true;
        });
    });
    document.getElementById('sorusulub-clear')?.addEventListener('click', () => clearChips('sorusulub-grid','sel-sorusulub'));

    // Satış olmayıb
    document.getElementById('satis-yox-btn')?.addEventListener('click', () => clearChips('satilib-grid','sel-satilib'));
    // Hamısı satılıb
    document.getElementById('satis-all-btn')?.addEventListener('click', () => {
        document.querySelectorAll('#satilib-grid .chip').forEach(chip => {
            chip.classList.add('sel-satilib');
            chip.querySelector('.chip-ico').textContent = '✓';
            const cb = chip.querySelector('input'); if (cb) cb.checked = true;
        });
    });
    document.getElementById('satis-clear')?.addEventListener('click', () => clearChips('satilib-grid','sel-satilib'));

    // Hamısı var (mövcud) — yoxdur sıfırlanır
    document.getElementById('movcud-all-btn')?.addEventListener('click', () => clearChips('yoxdur-grid','sel-yoxdur'));
    document.getElementById('movcud-clear')?.addEventListener('click', () => clearChips('yoxdur-grid','sel-yoxdur'));

    function clearChips(gridId, cls) {
        document.querySelectorAll(`#${gridId} .chip`).forEach(chip => {
            chip.classList.remove(cls);
            chip.querySelector('.chip-ico').textContent = '○';
            const cb = chip.querySelector('input'); if (cb) cb.checked = false;
        });
    }

    // ── RƏF seçimi ───────────────────────────────────────────────
    const refInput = document.getElementById('ref_val');
    document.querySelectorAll('.ref-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.ref-btn').forEach(b => b.classList.remove('sel'));
            btn.classList.add('sel');
            if (refInput) refInput.value = btn.dataset.val;
        });
    });

    // ── VALİDASİYA ───────────────────────────────────────────────
    document.getElementById('submit-btn')?.addEventListener('click', e => {
        const rayon = document.getElementById('rayon_id')?.value;
        const aptek = document.getElementById('aptek_ad')?.value?.trim();
        const ref   = document.getElementById('ref_val')?.value;
        if (!rayon) { showAlert('Rayon seçilməyib!'); e.preventDefault(); return; }
        if (!aptek) { showAlert('Aptekin adını daxil edin!'); e.preventDefault(); return; }
        if (!ref)   { showAlert('Rəf vəziyyəti seçilməyib!'); e.preventDefault(); return; }
    });

    // ── HESABATda filtr: bölgə → rayon ───────────────────────────
    const fBolge = document.getElementById('f_bolge');
    const fRayon = document.getElementById('f_rayon');
    if (fBolge && fRayon) {
        fBolge.addEventListener('change', () => {
            fRayon.innerHTML = '<option value="">Hamısı</option>';
            if (!fBolge.value) return;
            fetch('ajax.php?action=rayonlar&bolge_id=' + fBolge.value)
                .then(r => r.json())
                .then(data => data.forEach(r => fRayon.add(new Option(r.ad, r.id))));
        });
    }

    function showAlert(msg) {
        let el = document.getElementById('js-alert');
        if (!el) {
            el = document.createElement('div');
            el.id = 'js-alert';
            el.className = 'alert alert-err';
            document.querySelector('.wrap')?.prepend(el);
        }
        el.textContent = '⚠️ ' + msg;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => el?.remove(), 4000);
    }
});
