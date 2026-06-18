/**
 * 밥동무 API 공통 헬퍼
 * JWT Authorization 헤더를 자동으로 포함합니다.
 */

const API_BASE = '/api/v1';

/**
 * API 요청을 보냅니다.
 * @param {string} path - API 경로 (예: '/users/login')
 * @param {object} options - fetch 옵션
 * @returns {Promise<object>} 응답 JSON
 */
async function api(path, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  }).catch(() => {
    throw Object.assign(new Error('네트워크 연결을 확인해주세요.'), { status: 0 });
  });

  if (!response.ok) { // 문자열로 오든, 배열로 오든 문자열값 보여주도록 수정
    const error = await response.json().catch(() => ({ detail: '요청에 실패했어요.' }));
    const detail = error.detail;
    const message = Array.isArray(detail)
      ? detail.map(d => d.msg.replace(/^Value error,\s*/i, '')).join(', ')
      : (detail || '요청에 실패했어요.');
    const err = new Error(message);
    err.status = response.status;
    throw err;
  }

  // 204(요청은 성공했는데 돌려줄 데이터가 없을때)처럼 body가 없는 응답은 null 반환
  if (response.status === 204) return null;
  return response.json();
}

/**
 * 로그인 후 토큰을 저장합니다.
 */
function saveToken(token) {
  localStorage.setItem('access_token', token);
}

/**
 * 로그아웃합니다.
 */
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('currentUser');
  sessionStorage.removeItem('cachedUser');
  window.location.href = '/pages/login.html';
}

/**
 * 로그인 여부를 확인합니다.
 */
function isLoggedIn() {
  return !!localStorage.getItem('access_token');
}
