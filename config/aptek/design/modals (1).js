/**
 * modals.js
 * Modal açma/bağlama + Drug formu (ad + son istifadə tarixi)
 */

(function () {
  'use strict';

  /**
   * Modal açır
   * @param {string} id — modal element id (məs: modal-drug)
   */
  function openModal(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.add('modal--open');
    el.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');

    var first = el.querySelector('input, select, textarea, button:not([data-modal-close])');
    if (first) setTimeout(function () { first.focus(); }, 50);
  }

  /**
   * Modal bağlayır
   * @param {string|HTMLElement} idOrEl
   */
  function closeModal(idOrEl) {
    var el = typeof idOrEl === 'string' ? document.getElementById(idOrEl) : idOrEl;
    if (!el) return;
    el.classList.remove('modal--open');
    el.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
  }

  /* Global API */
  window.AnbarModal = { open: openModal, close: closeModal };

  document.addEventListener('DOMContentLoaded', function () {

    /* data-modal-open="drug" → #modal-drug */
    document.querySelectorAll('[data-modal-open]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var key = btn.getAttribute('data-modal-open');
        if (!key) return;
        openModal('modal-' + key);
      });
    });

    /* Backdrop / bağla düyməsi */
    document.querySelectorAll('[data-modal-close]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var modal = btn.closest('.modal');
        if (modal) closeModal(modal);
      });
    });

    /* ESC ilə bağla */
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var open = document.querySelector('.modal.modal--open');
      if (open) closeModal(open);
    });

    /* ---------- Drug formu — serverə POST (DB-yə yazılır) ---------- */
    var drugForm = document.getElementById('form-drug');
    if (drugForm) {
      drugForm.addEventListener('submit', function (e) {
        var nameInput = document.getElementById('drug_name');
        var expiryInput = document.getElementById('drug_expiry');
        var nameErr = document.getElementById('drug_name_error');
        var expiryErr = document.getElementById('drug_expiry_error');

        var name = (nameInput && nameInput.value || '').trim();
        var expiry = (expiryInput && expiryInput.value || '').trim();
        var ok = true;

        if (nameErr) nameErr.classList.toggle('hidden', !!name);
        if (nameInput) nameInput.classList.toggle('form-input--error', !name);
        if (!name) ok = false;

        if (expiryErr) expiryErr.classList.toggle('hidden', !!expiry);
        if (expiryInput) expiryInput.classList.toggle('form-input--error', !expiry);
        if (!expiry) ok = false;

        if (!ok) {
          e.preventDefault();
          return;
        }
        /* validdirsə normal POST — Django Medicine yaratır */
      });
    }
  });

})();
