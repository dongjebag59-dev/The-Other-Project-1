// ── 비밀번호 찾기 모달 ────────────────────────────────────────────
let _pwResetEmail = '';  // 1단계에서 입력한 이메일
let _pwResetToken = '';  // 서버가 준 reset_token

function showPwStep(n) {
  [1, 2, 3].forEach(i => {
    document.getElementById(`pw-step-${i}`).classList.toggle('hidden', i !== n);
  });
}

// 모달 열때마다 전부 초기화후 1단계로 리셋
function openPwResetModal() {
  _pwResetToken = '';
  _pwResetEmail = '';
  document.getElementById('pw-email').value = '';
  document.getElementById('pw-code').value = '';
  document.getElementById('pw-new').value = '';
  document.getElementById('pw-confirm').value = '';
  ['pw-step1-error', 'pw-step2-error', 'pw-step3-error'].forEach(id => {
    document.getElementById(id).classList.add('hidden');
  });
  showPwStep(1);
  document.getElementById('pw-reset-modal').classList.add('open');
  syncBodyLock();
}

function closePwResetModal() {
  document.getElementById('pw-reset-modal').classList.remove('open');
  syncBodyLock();
}

// 비밀번호 찾기 링크 클릭 -> 모달 열기
document.getElementById('forgot-pw-link')?.addEventListener('click', (e) => {
  e.preventDefault();
  openPwResetModal();
});

// X 버튼 클릭 -> 모달 닫기 (모달 바깥 영역 클릭시 닫히는거 삭제함)
document.getElementById('pw-reset-close')?.addEventListener('click', closePwResetModal);


// 1단계: 이메일 입력 → SMS 발송
document.getElementById('pw-step1-btn')?.addEventListener('click', async () => {
  const errEl = document.getElementById('pw-step1-error');
  errEl.classList.add('hidden');
  const email = document.getElementById('pw-email').value.trim();
  if (!email) {  // 빈칸일때 에러 표시
    errEl.textContent = '이메일을 입력해주세요.';
    errEl.classList.remove('hidden');
    return;
  }
  try {
    const data = await api('/users/password/reset/request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
    _pwResetEmail = email;
    document.getElementById('pw-phone-hint').textContent =
      `가입된 계정이 있다면 ${data.phone_masked}로 인증코드를 발송했습니다.`;
    showPwStep(2);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

// 2단계: 인증코드 재발송 (2단계 안에서 재요청)
document.getElementById('pw-resend-link')?.addEventListener('click', async (e) => {
  e.preventDefault();
  const errEl = document.getElementById('pw-step2-error');
  errEl.classList.add('hidden');
  try {
    const data = await api('/users/password/reset/request', {
      method: 'POST',
      body: JSON.stringify({ email: _pwResetEmail }),
    });
    document.getElementById('pw-phone-hint').textContent =
      `가입된 계정이 있다면 ${data.phone_masked}로 인증코드를 재발송했습니다.`;
    document.getElementById('pw-code').value = '';
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

// 2단계: SMS 코드 확인 → reset_token 발급
document.getElementById('pw-step2-btn')?.addEventListener('click', async () => {
  const errEl = document.getElementById('pw-step2-error');
  errEl.classList.add('hidden');
  const code = document.getElementById('pw-code').value.trim();
  if (code.length !== 6) {
    errEl.textContent = '6자리 인증코드를 입력해주세요.';
    errEl.classList.remove('hidden');
    return;
  }
  try {
    const data = await api('/users/password/reset/verify', {
      method: 'POST',
      body: JSON.stringify({ email: _pwResetEmail, code }),
    });
    _pwResetToken = data.reset_token;
    showPwStep(3);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

// 3단계: 새 비밀번호 설정
// api()는 localStorage 토큰을 항상 우선해서 reset_token 전달 불가 → fetch 직접 사용
document.getElementById('pw-step3-btn')?.addEventListener('click', async () => {
  const errEl = document.getElementById('pw-step3-error');
  errEl.classList.add('hidden');
  const newPw = document.getElementById('pw-new').value;
  const confirmPw = document.getElementById('pw-confirm').value;
  if (newPw.length < 8) {
    errEl.textContent = '비밀번호는 8자 이상이어야 합니다.';
    errEl.classList.remove('hidden');
    return;
  }
  if (newPw !== confirmPw) {
    errEl.textContent = '비밀번호가 일치하지 않습니다.';
    errEl.classList.remove('hidden');
    return;
  }
  try {
    const response = await fetch('/api/v1/users/password/reset', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${_pwResetToken}`,
      },
      body: JSON.stringify({ new_password: newPw, new_password_confirm: confirmPw }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '요청에 실패했어요.' }));
      throw new Error(error.detail || '요청에 실패했어요.');
    }
    closePwResetModal();
    await showResultModal('비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요.', 'success');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

// ──────────────────────────────────────────────────────────────────
const params = new URLSearchParams(window.location.search);
// url의 # 이후 전체 문자열 + '#' 제거
const hashParams = new URLSearchParams(window.location.hash.slice(1));

// 회원가입 직후 넘어온 경우 안내 메시지 표시
if (params.get('registered') === '1') {
  document.getElementById('register-notice').classList.remove('hidden');
}

// 카카오 에러: 취소하거나 카카오 API 오류 발생
if (params.get('kakao_error') === '1') {
  const errorMsg = document.getElementById('error-msg');
  errorMsg.textContent = '카카오 로그인에 실패했습니다. 다시 시도해주세요.';
  errorMsg.classList.remove('hidden');
}

// 카카오 로그인 성공 (기존 유저): 콜백에서 kakao_token 받아서 로그인 처리
const kakaoToken = hashParams.get('kakao_token');
if (kakaoToken) {
  // 토큰 읽은후 주소창에서 #kakao_token=... 제거
  history.replaceState(null, '', window.location.pathname + window.location.search);
  (async () => {
    const errorMsg = document.getElementById('error-msg');
    try {
      saveToken(kakaoToken);

      const user = await api('/users/me');
      const normalizedRole = String(user.user_role ?? '').trim().toLowerCase();

      localStorage.setItem(
        'currentUser',
        JSON.stringify({
          user_id: user.user_id,
          name: user.name,
          user_role: normalizedRole,
        }),
      );

      if (normalizedRole === 'admin') { window.location.replace('/pages/admin.html'); return; }
      if (normalizedRole === 'guardian') { window.location.replace('/pages/guardian.html'); return; }
      if (normalizedRole === 'volunteer') { window.location.replace('/pages/hosting-match.html'); return; }

      throw new Error(`알 수 없는 user_role: ${user.user_role}`);
    } catch (err) {
      errorMsg.textContent = '카카오 로그인 처리 중 오류가 발생했습니다.';
      errorMsg.classList.remove('hidden');
    }
  })();
}

// 이메일/비밀번호 로그인
document.querySelector('#login-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();

  const errorMsg = document.querySelector('#error-msg');
  errorMsg.classList.add('hidden');

  try {
    const data = await api('/users/login', {
      method: 'POST',
      body: JSON.stringify({
        email: document.querySelector('#email').value,
        password: document.querySelector('#password').value,
      }),
    });

    console.log('login response:', data);
    
    // access token 저장, 이전 세션 캐시 클리어
    saveToken(data.access_token);
    sessionStorage.removeItem('cachedUser');
    
    // 현재 로그인 사용자 정보 조회
    const user = await api('/users/me');
    
    // User_role 값 문자열화 + 소문자 변환 + 공백 제거 
    const normalizedRole = String(user.user_role ?? '').trim().toLowerCase();
    
    // authGuard.js가 쓰는 currentUser 저장
    localStorage.setItem(
      'currentUser',
      JSON.stringify({
        user_id: user.user_id,
        name: user.name,
        user_role: normalizedRole,
      }),
    );

    // cert_flag 미승인(guardian/volunteer)은 마이페이지로 — 서류 제출 필요
    if (normalizedRole !== 'admin' && user.cert_flag !== 'approved') {
      window.location.replace('/pages/mypage.html');
      return;
    }

    // redirect 파라미터 있으면 원래 페이지로 복귀 (QR 체크인 등) — 같은 origin만 허용
    const redirectUrl = params.get('redirect');
    if (redirectUrl) {
      try {
        const decoded = decodeURIComponent(redirectUrl);
        if (new URL(decoded).origin === window.location.origin) {
          window.location.replace(decoded);
          return;
        }
      } catch (e) {
        console.warn('redirect 파라미터가 유효하지 않은 URL입니다:', e);
      }
    }

    // 역할별 페이지 이동
    // 로그인 페이지를 히스토리에 남기지 않아서 뒤로가기 동작이 덜 꼬일 수 있음(replace)
    if (normalizedRole === 'admin') {
      window.location.replace('/pages/admin.html');
      return;
    }

    if (normalizedRole === 'guardian') {
      window.location.replace('/pages/guardian.html');
      return;
    }

    if (normalizedRole === 'volunteer') {
      window.location.replace('/pages/hosting-match.html');
      return;
    }

    throw new Error(`알 수 없는 user_role: ${user.user_role}`);
  } catch (err) {
    errorMsg.textContent = err.message;
    errorMsg.classList.remove('hidden');
  }
});