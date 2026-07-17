/**
 * dashboard.js
 * Ümumi UI davranışı — sidebar, bildirişlər, asistent formu
 * Chart məntiqi charts.js-dədir; buraya qarışdırmırıq.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    /* ---------- Asistent formu — boş göndərmənin qarşısını alır ---------- */
    var aiForm = document.querySelector('.ai-input');
    if (aiForm) {
      aiForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var input = aiForm.querySelector('input');
        if (!input || !input.value.trim()) return;

        /* Demo: mesajı konsola yazırıq — backendə bağlananda buranı dəyiş */
        console.log('[Anbar Asistent]', input.value.trim());
        input.value = '';
      });
    }

    /* ---------- Aktiv nav linkinə scroll (uzun menyu üçün) ---------- */
    var activeLink = document.querySelector('.nav-link--active');
    if (activeLink && activeLink.scrollIntoView) {
      activeLink.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    /* ---------- CTA düymələr — modal açanları nəzərə almır ---------- */
    document.querySelectorAll('.btn-cyan:not([data-modal-open])').forEach(function (btn) {
      btn.addEventListener('click', function () {
        console.log('[CTA]', btn.textContent.trim());
      });
    });
  });
})();
