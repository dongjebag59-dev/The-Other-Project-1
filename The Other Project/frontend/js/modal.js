// ── 공통 모달 ─────────────────────────────────────────────
// showResultModal(message, type?)  → Promise (확인 클릭 시 resolve)
// openConfirmModal({ title, message, confirmText?, cancelText?, onConfirm? })

(function () {
  let _injected = false;
  let _resultResolver = null;
  let _confirmHandler = null;

  function _inject() {
    if (_injected) return;
    _injected = true;

    const html = `
<div id="result-modal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="result-modal-title">
  <div id="result-modal-panel" class="modal-panel result-modal info">
    <div class="modal-header">
      <h3 id="result-modal-title">안내</h3>
      <button id="result-modal-close-btn" type="button" class="modal-close-button" aria-label="닫기">×</button>
    </div>
    <div class="modal-body">
      <div id="result-modal-message" class="modal-message"></div>
      <div class="modal-actions">
        <button id="result-modal-confirm-btn" type="button" class="btn btn-primary btn-sm">확인</button>
      </div>
    </div>
  </div>
</div>

<div id="confirm-modal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-modal-title">
  <div class="modal-panel">
    <div class="modal-header">
      <h3 id="confirm-modal-title">안내</h3>
      <button id="confirm-modal-close-btn" type="button" class="modal-close-button" aria-label="닫기">×</button>
    </div>
    <div class="modal-body">
      <div id="confirm-modal-message" class="modal-message"></div>
      <div class="modal-actions">
        <button id="confirm-modal-cancel-btn" type="button" class="btn btn-ghost btn-sm">취소</button>
        <button id="confirm-modal-confirm-btn" type="button" class="btn btn-primary btn-sm">확인</button>
      </div>
    </div>
  </div>
</div>`;

    const container = document.createElement('div');
    container.innerHTML = html;
    document.body.appendChild(container);

    document.getElementById('result-modal-close-btn').addEventListener('click', closeResultModal);
    document.getElementById('result-modal-confirm-btn').addEventListener('click', closeResultModal);
    document.getElementById('result-modal').addEventListener('click', function (e) {
      if (e.target === e.currentTarget) closeResultModal();
    });

    document.getElementById('confirm-modal-close-btn').addEventListener('click', closeConfirmModal);
    document.getElementById('confirm-modal-cancel-btn').addEventListener('click', closeConfirmModal);
    document.getElementById('confirm-modal-confirm-btn').addEventListener('click', _handleConfirm);
    document.getElementById('confirm-modal').addEventListener('click', function (e) {
      if (e.target === e.currentTarget) closeConfirmModal();
    });
  }

  function _syncBodyLock() {
    const anyOpen =
      document.querySelectorAll('.modal-overlay.open').length > 0;
    document.body.classList.toggle('modal-open', !!anyOpen);
  }
  
  function _titleFor(type) {
    if (type === 'success') return '완료';
    if (type === 'error') return '오류';
    return '안내';
  }

  async function _handleConfirm() {
    if (!_confirmHandler) { closeConfirmModal(); return; }
    const fn = _confirmHandler;
    closeConfirmModal();
    await fn();
  }

  // ── 공개 API ──────────────────────────────────────────

  window.showResultModal = function (message, type = 'info') {
    _inject();
    return new Promise((resolve) => {
      const panel = document.getElementById('result-modal-panel');
      panel.className = `modal-panel result-modal ${type}`;
      document.getElementById('result-modal-title').textContent = _titleFor(type);
      document.getElementById('result-modal-message').textContent = message;
      document.getElementById('result-modal').classList.add('open');
      _resultResolver = resolve;
      _syncBodyLock();
    });
  };

  window.closeResultModal = function () {
    _inject();
    document.getElementById('result-modal').classList.remove('open');
    if (_resultResolver) {
      const fn = _resultResolver;
      _resultResolver = null;
      fn();
    }
    _syncBodyLock();
  };

  window.openConfirmModal = function ({ title, message, confirmText = '확인', cancelText = '취소', onConfirm = null }) {
    _inject();
    document.getElementById('confirm-modal-title').textContent = title;
    document.getElementById('confirm-modal-message').textContent = message;
    document.getElementById('confirm-modal-confirm-btn').textContent = confirmText;
    document.getElementById('confirm-modal-cancel-btn').textContent = cancelText;
    _confirmHandler = onConfirm;
    document.getElementById('confirm-modal').classList.add('open');
    _syncBodyLock();
  };

  window.closeConfirmModal = function () {
    _inject();
    document.getElementById('confirm-modal').classList.remove('open');
    _confirmHandler = null;
    _syncBodyLock();
  };

  window.syncBodyLock = _syncBodyLock;
})();
