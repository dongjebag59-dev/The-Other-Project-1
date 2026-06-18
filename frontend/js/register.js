import { mapKakaoAddressToPayload } from '/js/addressMapper.js';
import { normalizePhone } from './format-utils.js';

// 카카오 모드 감지 (?kakao=true&setup_token=xxx 로 넘어온 경우)
const params = new URLSearchParams(window.location.search);
const isKakao = params.get('kakao') === 'true';
const setupToken = params.get('setup_token');

if (isKakao) {
  // 카카오 안내 배너 표시
  document.getElementById('kakao-banner')?.classList.remove('hidden');
  // 카카오 연결 완료 후 불필요한 UI 숨김
  document.querySelector('.kakao-login-btn')?.classList.add('hidden');
  document.getElementById('kakao-hint')?.classList.add('hidden');
  document.querySelector('.login-divider')?.classList.add('hidden');
  document.getElementById('email-signup-label')?.classList.add('hidden');
  // 카카오 유저에게 불필요한 필드 숨김
  ['#email', '#password', '#password-confirm'].forEach(id => {
    document.querySelector(id)?.closest('.form-group')?.classList.add('hidden');
  });
}

// 보호자 서류 종류 셀렉트 변경 시 파일 업로드 라벨 동기화
document.querySelector('#doc-guardian-type')?.addEventListener('change', (e) => {
  const label = document.querySelector('#doc-family-label');
  label.textContent = e.target.options[e.target.selectedIndex].text;
});

// 봉사자, 보호자 탭 전환 및 서류 필드 토글
document.querySelectorAll('.tab[data-role]').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab[data-role]').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelector('#role').value = tab.dataset.role;

    const selectedRole = tab.dataset.role;
    document.querySelectorAll('[data-role-doc]').forEach(el => {
      el.classList.toggle('hidden', el.dataset.roleDoc !== selectedRole);
    });
  });
});

// 파일 선택 시 파일명 표시 + 형식/크기 인라인 검증
const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'pdf', 'hwp', 'docx'];
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

document.querySelectorAll('input[type="file"]').forEach(input => {
  input.addEventListener('change', () => {
    const file = input.files[0];
    const span = input.closest('label').querySelector('.doc-upload-text');
    span.textContent = file ? file.name : '파일 선택';

    const hint = input.closest('.form-group').querySelector('.doc-hint');
    let errorEl = input.closest('.form-group').querySelector('.alert-error');

    if (!file) {
      errorEl?.remove();
      return;
    }

    const ext = file.name.split('.').pop().toLowerCase();
    let errorMsg = null;
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      errorMsg = '지원하지 않는 파일 형식입니다. 알맞은 형식의 파일을 다시 첨부해주세요.(허용: jpg, png, pdf, hwp, docx)';
    } else if (file.size > MAX_FILE_SIZE) {
      errorMsg = '파일 크기가 5MB를 초과했습니다. 5MB보다 작은 파일을 첨부해주세요.';
    }

    if (errorMsg) {
      if (!errorEl) {
        errorEl = document.createElement('p');
        errorEl.className = 'alert alert-error';
        hint.after(errorEl);
      }
      errorEl.textContent = errorMsg;
    } else {
      errorEl?.remove();
    }
  });
});

// 주소 검색
let registerAddressData = null;

document.querySelector('#btn-search-address')?.addEventListener('click', () => {
  if (!window.daum?.Postcode) {
    showResultModal('주소 검색을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.', 'error');
    return;
  }

  new window.daum.Postcode({
    oncomplete(data) {
      const parts = [data.sido, data.sigungu, data.bname].filter(Boolean);
      document.querySelector('#district').value = parts.join(' ');
      registerAddressData = mapKakaoAddressToPayload(data);
    },
  }).open();
});

// SMS 인증
let phoneVerified = false;

// 인증하기 버튼
document.querySelector('#btn-send-code')?.addEventListener('click', async () => {
  const phone = normalizePhone(document.querySelector('#phone').value);
  if (!phone) {
    showResultModal('올바른 전화번호를 입력해주세요. (예: 01012345678)', 'error');
    return;
  }

  const btn = document.querySelector('#btn-send-code');
  btn.disabled = true;
  btn.textContent = '발송 중...';

  try {
    await api('/users/phone/send', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phone }),
    });
    document.querySelector('#verify-group').classList.remove('hidden');
    document.querySelector('#verify-msg').textContent = '인증번호가 발송됐습니다. 3분 이내에 입력해주세요.';
    document.querySelector('#verify-msg').style.color = '';
    phoneVerified = false;
    btn.textContent = '재발송';
  } catch (err) {
    showResultModal(err.message || 'SMS 발송에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error');
    btn.textContent = '인증하기';
  } finally {
    btn.disabled = false;
  }
});

// 확인 버튼
document.querySelector('#btn-verify-code')?.addEventListener('click', async () => {
  const phone = normalizePhone(document.querySelector('#phone').value);
  const code = document.querySelector('#verify-code').value.trim();
  const verifyMsg = document.querySelector('#verify-msg');

  if (!code) {
    verifyMsg.textContent = '인증번호를 입력해주세요.';
    verifyMsg.style.color = 'var(--color-error, #e53e3e)';
    return;
  }

  const btn = document.querySelector('#btn-verify-code');
  btn.disabled = true;

  try {
    await api('/users/phone/verify', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phone, code }),
    });
    phoneVerified = true;
    verifyMsg.textContent = '인증이 완료됐습니다.';
    verifyMsg.style.color = 'var(--color-success, #38a169)';
    document.querySelector('#btn-send-code').disabled = true;
    btn.disabled = true;
    document.querySelector('#phone').readOnly = true;
    document.querySelector('#verify-code').readOnly = true;
  } catch (err) {
    phoneVerified = false;
    verifyMsg.textContent = err.message || '인증에 실패했습니다.';
    verifyMsg.style.color = 'var(--color-error, #e53e3e)';
    btn.disabled = false;
  }
});

// 전화번호 변경 시(번호 입력폼 수정 시) 인증 초기화
document.querySelector('#phone')?.addEventListener('input', () => {
  phoneVerified = false;
  document.querySelector('#verify-group').classList.add('hidden');
  document.querySelector('#verify-code').value = '';
  document.querySelector('#btn-send-code').disabled = false;
  document.querySelector('#btn-send-code').textContent = '인증하기';
});

// 파일 업로드 함수(파일: json에 못담아서 multipart 씀)
async function uploadDocument(token, documentType, file) {
  const formData = new FormData();  // FormData: multipart 요청 생성
  formData.append('document_type', documentType);
  formData.append('file', file);

  // api(): content-type json 강제. boundary값 X
  // fetch: content-type 자동 설정, boundary값 O(multipart: 파싱 때문에 파일경계값 필요)
  const response = await fetch('/api/v1/users/me/documents', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },  // 토큰만 직접 설정
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '서류 업로드에 실패했어요.' }));
    const detail = error.detail;
    const message = Array.isArray(detail)
      ? detail.map(d => d.msg.replace(/^Value error,\s*/i, '')).join(', ')
      : (detail || '서류 업로드에 실패했어요.');
    const err = new Error(message);
    err.status = response.status;  // http 상태 코드를 에러 객체에 담음(catch용)
    throw err;
  }
  return response.json();
}

// 회원가입 폼 제출
document.querySelector('#register-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();

  const errorMsg = document.querySelector('#error-msg');

  // 공통 검증 — 카카오/일반 모두
  if (!document.querySelector('#name').value.trim()) {
    errorMsg.textContent = '이름을 입력해주세요.';
    errorMsg.classList.remove('hidden');
    return;
  }

  // 일반가입 전용 검증 — 카카오는 비번, 폰번 필드 X
  if (!isKakao) {
    const emailInput = document.querySelector('#email');
    if (!emailInput.value.trim()) {
      errorMsg.textContent = '이메일을 입력해주세요.';
      errorMsg.classList.remove('hidden');
      return;
    }
    if (!emailInput.validity.valid) {
      errorMsg.textContent = '올바른 이메일 형식을 입력해주세요.';
      errorMsg.classList.remove('hidden');
      return;
    }

    const password = document.querySelector('#password').value;
    const passwordConfirm = document.querySelector('#password-confirm').value;

    if (password.length < 8) {
      errorMsg.textContent = '비밀번호는 8자 이상이어야 합니다.';
      errorMsg.classList.remove('hidden');
      return;
    }

    if (password !== passwordConfirm) {
      errorMsg.textContent = '비밀번호가 일치하지 않습니다.';
      errorMsg.classList.remove('hidden');
      return;
    }

  }

  if (!phoneVerified) {
    errorMsg.textContent = '전화번호 인증을 완료해주세요.';
    errorMsg.classList.remove('hidden');
    return;
  }

  if (!document.querySelector('#district').value) {
    errorMsg.textContent = '주소를 검색해주세요.';
    errorMsg.classList.remove('hidden');
    return;
  }

  errorMsg.classList.add('hidden');

  const role = document.querySelector('#role').value;
  const idFile = document.querySelector('#doc-id').files[0];
  const extraFile = role === 'volunteer'
    ? document.querySelector('#doc-criminal').files[0]
    : document.querySelector('#doc-family').files[0];

  if (!idFile || !extraFile) {
    const confirmed = await new Promise((resolve) => {
      let resolved = false;
      const done = (value) => { if (!resolved) { resolved = true; resolve(value); } };
      openConfirmModal({
        title: '서류 미제출 확인',
        message: '서류를 모두 제출하지 않아도 가입은 가능하지만,\n관리자의 승인이 반려될 수 있습니다. 계속하시겠습니까?',
        confirmText: '계속 진행',
        cancelText: '돌아가기',
        onConfirm: () => done(true),
      });
      document.getElementById('confirm-modal-cancel-btn')?.addEventListener('click', () => done(false), { once: true });
      document.getElementById('confirm-modal-close-btn')?.addEventListener('click', () => done(false), { once: true });
      document.getElementById('confirm-modal')?.addEventListener('click', (e) => { if (e.target === e.currentTarget) done(false); }, { once: true });
    });
    if (!confirmed) return;
  }

  const submitBtn = document.querySelector('#register-form button[type="submit"]');
  submitBtn.disabled = true;  // 가입 제출 시작하면 버튼 비활성화

  let token = null; // catch에서 가입 성공 판단 위해 try 바깥에 선언

  try {
    let result;

    if (isKakao) {
      // 1-카카오) kakao-setup 호출 → 이 시점에 DB에 계정 생성
      // setup_token: 카카오 인증 완료 증거 (콜백에서 발급한 10분짜리 토큰)
      result = await api('/users/kakao-setup', {
        method: 'POST',
        body: JSON.stringify({
          setup_token: setupToken,
          name: document.querySelector('#name').value,
          phone_number: normalizePhone(document.querySelector('#phone').value),
          user_role: role,
          address: registerAddressData,
        }),
      });
    } else {
      // 1-일반) 일반 회원가입
      result = await api('/users/register', {
        method: 'POST',
        body: JSON.stringify({
          email: document.querySelector('#email').value,
          password: document.querySelector('#password').value,
          password_confirm: document.querySelector('#password-confirm').value,
          name: document.querySelector('#name').value,
          phone_number: normalizePhone(document.querySelector('#phone').value),
          user_role: role,
          address: registerAddressData,
        }),
      });
    }

    // 2) 토큰 저장 (서류 업로드 시 인증에 필요)
    token = result.access_token;
    // saveToken 삭제 → 회원가입 후 자동 로그인 방지, 서류 업로드엔 token 변수 직접 사용

    // 3) 신분증 사본 업로드 (선택)
    if (idFile) {
      await uploadDocument(token, 'identity_copy', idFile);
    }

    // 4) 역할별 추가 서류 업로드 (선택)
    if (extraFile) {
      const documentType = role === 'volunteer'
        ? 'criminal_record'
        : document.querySelector('#doc-guardian-type').value;
      await uploadDocument(token, documentType, extraFile);
    }

    window.location.href = '/pages/login.html?registered=1';
  } catch (err) {
    submitBtn.disabled = false;  // 가입 실패하면 다시 버튼 활성화
    if (token) {
      // 서류는 회원가입 필수값이 아님
      // 서류 업로드 실패해도 계정유지(가입처리), 로그인 후 마이페이지에서 재업로드 가능
      // 503: R2 서버 문제 → 안내 문구로 표시
      // 400: 형식 오류/크기 초과 → 백엔드 메시지(유저가 수정할수있도록)
      const msg = err.status === 503
        ? '서류 업로드에 실패했습니다.\n가입은 완료됐으니 로그인 후 마이페이지에서 다시 업로드해주세요.'
        : `서류 업로드 오류: ${err.message}\n가입은 완료됐으니 로그인 후 마이페이지에서 다시 업로드해주세요.`;
      await showResultModal(msg, 'info');
      window.location.href = '/pages/login.html';
    } else {
      errorMsg.textContent = err.message;
      errorMsg.classList.remove('hidden');
    }
  }
});
