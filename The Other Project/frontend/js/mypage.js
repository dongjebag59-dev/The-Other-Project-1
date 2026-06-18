import { mapKakaoAddressToPayload } from '/js/addressMapper.js';
import { syncUserCache } from './authGuard.js';
import { KST_TIME_ZONE, parseApiDateTime } from './format-utils.js';

// 로그인 안 했으면 로그인 페이지로 이동
if (!isLoggedIn()) {  // api.js 함수
  window.location.href = '/pages/login.html';
}

// 서류 유형 한글 이름 매핑
const DOC_TYPE_LABELS = {
  criminal_record: '범죄경력조회서',
  welfare_cert: '복지관 인증서류',
  family_cert: '가족관계증명서',
  identity_copy: '신분증 사본',
};

// 날짜 포맷 (UTC → KST 변환 후 표시)
function formatDateTime(isoString) {
  const date = parseApiDateTime(isoString);
  if (!date) return '-';
  return date.toLocaleString('ko-KR', {
    timeZone: KST_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

// 서류 파일 업로드 (register.js와 같은 multipart 방식)
// api() 대신 fetch 사용 - content-type boundary 자동 설정 필요
async function uploadDocument(documentType, file) {
  const formData = new FormData();
  formData.append('document_type', documentType);
  formData.append('file', file);
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/v1/users/me/documents', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '서류 업로드에 실패했어요.' }));
    const detail = error.detail;
    const message = Array.isArray(detail)
      ? detail.map(d => d.msg.replace(/^Value error,\s*/i, '')).join(', ')
      : (detail || '서류 업로드에 실패했어요.');
    throw new Error(message);
  }
  return response.json();
}

// 업로드된 서류 (승인완료 상태면 삭제 버튼 숨김)
function renderUploadedSlot(doc, label, isLocked) {
  const fileName = doc.document_url.split('/').pop();  // R2 URL에서 파일명만 추출
  const deleteBtn = isLocked
    ? ''
    : `<button class="btn btn-sm btn-danger delete-doc-btn" data-doc-id="${doc.document_id}" style="flex-shrink:0;">삭제</button>`;
  return `
    <div class="list-item" style="background:var(--surface); border:1px solid var(--border-light); border-radius:var(--radius-md); margin-bottom:8px;">
      <div style="min-width:0;">
        <div style="font-weight:600; font-size:14px;">${label}</div>
        <a class="open-doc-link" data-doc-id="${doc.document_id}" href="#"
          style="font-size:12px; color:var(--primary); margin-top:2px; display:block; word-break:break-all;">${fileName}</a>
        <div style="font-size:12px; color:var(--muted);">${formatDateTime(doc.created_at)} 업로드</div>
      </div>
      ${deleteBtn}
    </div>`;
}

// 미업로드 서류 (업로드 버튼 포함)
function renderEmptySlot(docType, label) {
  return `
    <div class="list-item" style="background:var(--surface); border:1px solid var(--border-light); border-radius:var(--radius-md); margin-bottom:8px;">
      <div>
        <div style="font-weight:600; font-size:14px;">${label}</div>
        <div style="font-size:12px; color:var(--muted);">미업로드</div>
      </div>
      <label class="btn btn-sm btn-primary" style="cursor:pointer; flex-shrink:0;">
        업로드
        <input type="file" class="upload-input"
          style="display:none;"
          data-doc-type="${docType}"
          accept=".jpg,.jpeg,.png,.pdf,.hwp,.docx">
      </label>
    </div>`;
}

// 보호자 추가 서류 미업로드 (서류 종류 선택 셀렉트 포함)
function renderEmptyGuardianSlot() {
  return `
    <div class="list-item" style="background:var(--surface); border:1px solid var(--border-light); border-radius:var(--radius-md); margin-bottom:8px;">
      <div>
        <div style="font-weight:600; font-size:14px;">보호자 인증서류</div>
        <div style="font-size:12px; color:var(--muted);">미업로드</div>
      </div>
      <div style="display:flex; gap:8px; align-items:center; flex-shrink:0;">
        <select id="guardian-doc-type"
          style="padding:8px 10px; border:1.5px solid var(--border); border-radius:var(--radius-md); font-size:13px; font-family:var(--font-body); background:var(--surface); color:var(--text);">
          <option value="welfare_cert">복지관 인증서류</option>
          <option value="family_cert">가족관계증명서</option>
        </select>
        <label class="btn btn-sm btn-primary" style="cursor:pointer;">
          업로드
          <input type="file" class="upload-input guardian-upload"
            style="display:none;"
            accept=".jpg,.jpeg,.png,.pdf,.hwp,.docx">
        </label>
      </div>
    </div>`;
}

// 역할에 맞는 서류 슬롯 전체 렌더링
// 봉사자: 신분증 + 범죄경력 / 보호자: 신분증 + 복지관or가족
function renderDocumentSlots(docs, userRole, certFlag) {
  const container = document.getElementById('docs-list');
  const isLocked = certFlag === 'approved';
  // 승인완료면 삭제 버튼 비활성화
  // certflag 받아서 approved인지 판단하고 isLocked 만들어 각 서류 슬롯에 넘김

  const idDoc = docs.find(d => d.document_type === 'identity_copy');

  // 공통: 신분증 사본
  let html = idDoc ? renderUploadedSlot(idDoc, '신분증 사본', isLocked) : renderEmptySlot('identity_copy', '신분증 사본');

  if (userRole === 'volunteer') {
    const crimDoc = docs.find(d => d.document_type === 'criminal_record');
    html += crimDoc
      ? renderUploadedSlot(crimDoc, '범죄경력조회서', isLocked)
      : renderEmptySlot('criminal_record', '범죄경력조회서');
  } else if (userRole === 'guardian') {
    const guardianDoc = docs.find(d => d.document_type === 'welfare_cert' || d.document_type === 'family_cert');
    html += guardianDoc
      ? renderUploadedSlot(guardianDoc, DOC_TYPE_LABELS[guardianDoc.document_type], isLocked)
      : renderEmptyGuardianSlot();
  }

  container.innerHTML = html;
}

function setStats(entries) {
  entries.forEach(({ id, value, label }) => {
    document.getElementById(`stat-val-${id}`).textContent = value;
    document.getElementById(`stat-label-${id}`).textContent = label;
  });
}

async function loadStats(role) {
  try {
    const s = await api(`/users/me/stats/${role}`);
    if (role === 'volunteer') {
      setStats([
        { id: 1, value: `${(s.total_volunteer_minutes / 60).toFixed(1)}h`, label: '누적 봉사시간' },
        { id: 2, value: s.visit_count,   label: '방문 횟수' },
        { id: 3, value: s.review_count,  label: '작성 후기' },
        { id: 4, value: s.senior_count,  label: '만난 어르신' },
      ]);
    } else {
      setStats([
        { id: 1, value: s.senior_count,            label: '어르신 수' },
        { id: 2, value: s.active_hosting_count,    label: '호스팅 중' },
        { id: 3, value: s.cancelled_hosting_count, label: '호스팅 취소' },
        { id: 4, value: s.completed_hosting_count, label: '호스팅 완료' },
      ]);
    }
  } catch {
    document.querySelector('.stats-grid')?.remove();
  }
}

// 서류 목록 로드
// 즉시실행함수에서 me.user_role, me.cert_flag를 저장해두는 전역변수
let currentUserRole = null;
let currentCertFlag = null;

// api 호출 후 렌더링
async function loadDocuments() {
  try {  // 서류목록 렌더링할때 현재역할, 현재인증상태 같이 넘김
    const docs = await api('/users/me/documents');
    renderDocumentSlots(docs, currentUserRole, currentCertFlag);
  } catch {
    document.getElementById('docs-list').innerHTML =
      '<p style="color:var(--muted); font-size:14px; padding:12px 0;">서류 목록을 불러오지 못했어요.</p>';
  }
}

// 서류 업로드/삭제 후 인증 상태 뱃지 최신화
async function refreshCertBadge() {
  try {
    const me = await api('/users/me');
    syncUserCache(me);
    
    currentCertFlag = me.cert_flag;  // 전역변수 갱신 (loadDocuments가 최신 상태로 렌더링하도록)
    const certBadge = document.getElementById('cert-badge');
    if (me.cert_flag === 'approved') {
      certBadge.innerHTML = '<span class="badge badge-open">승인 완료</span>';
    } else if (me.cert_flag === 'pending') {
      certBadge.innerHTML = '<span class="badge badge-pending">검토 중</span>';
    } else if (me.cert_flag === 'rejected') {
      certBadge.innerHTML = '<span class="badge badge-cancelled">반려됨</span>';
    }
    const rejectSection = document.getElementById('reject-reason-section');
    const rejectMsg = document.getElementById('reject-reason-msg');
    if (me.cert_flag === 'rejected' && me.cert_reject_reason) {
      rejectMsg.textContent = me.cert_reject_reason;
      rejectSection.classList.remove('hidden');
    } else {
      rejectSection.classList.add('hidden');
    }
  } catch {
    currentCertFlag = 'pending';  // 실패 시 업로드로 인해 pending이 됐을 것이므로 fallback
  }
}

// 서류 클릭 이벤트 위임 (파일명 링크 열기 + 삭제 버튼)
document.getElementById('docs-list')?.addEventListener('click', async (e) => {
  // 파일명 링크 클릭 → presigned URL로 새 탭 열기
  const docLink = e.target.closest('.open-doc-link');
  if (docLink) {
    e.preventDefault();
    const docId = docLink.dataset.docId;
    try {
      const { url } = await api(`/users/documents/${docId}/presigned-url`);
      window.open(url, '_blank', 'noopener');
    } catch {
      showResultModal('서류를 불러올 수 없어요. 잠시 후 다시 시도해주세요.', 'error');
    }
    return;
  }

  // 삭제 버튼 클릭
  const deleteBtn = e.target.closest('.delete-doc-btn');
  if (!deleteBtn) return;
  const docId = deleteBtn.dataset.docId;
  openConfirmModal({
    title: '서류 삭제',
    message: '이 서류를 삭제하시겠어요?',
    confirmText: '삭제',
    cancelText: '취소',
    onConfirm: async () => {
      try {
        await api(`/users/me/documents/${docId}`, { method: 'DELETE' });
        await loadDocuments();
      } catch (err) {
        await showResultModal(err.message, 'error');
      }
    },
  });
});

// 서류 업로드 (change 이벤트 위임)
document.getElementById('docs-list')?.addEventListener('change', async (e) => {
  if (!e.target.classList.contains('upload-input')) return;
  const file = e.target.files[0];
  if (!file) return;

  // 보호자 추가 서류는 셀렉트에서 타입 읽기, 나머지는 data-doc-type 사용
  const docType = e.target.classList.contains('guardian-upload')
    ? e.target.closest('.list-item').querySelector('#guardian-doc-type').value
    : e.target.dataset.docType;
  try {
    await uploadDocument(docType, file);
    await refreshCertBadge();  // currentCertFlag 먼저 갱신
    await loadDocuments();     // 갱신된 cert 상태로 서류 슬롯 렌더링
  } catch (err) {
    await showResultModal(`업로드 실패: ${err.message}`, 'error');
  }
});

// 페이지 진입 시 유저 정보 (일반/카카오 로그인별 비밀번호 변경폼 노출 여부)
(async () => {
  try {
    const me = await api('/users/me');
    syncUserCache(me);
    
    // 프로필 카드 채우기
    const roleLabel = { volunteer: '봉사자', guardian: '보호자', admin: '관리자' }[me.user_role] ?? me.user_role;
    document.getElementById('profile-avatar').textContent = me.name[0];
    document.getElementById('profile-name').textContent = me.name;
    document.getElementById('profile-role-district').textContent = `${roleLabel} · ${me.address.road_address ?? ''}`;
    const contactParts = [me.email, me.phone_number].filter(Boolean);
    document.getElementById('profile-contact').textContent = contactParts.join(' · ');

    // 내 정보 섹션
    document.getElementById('user-name').textContent = me.name;
    document.getElementById('user-email').textContent = me.email;
    document.getElementById('user-phone').textContent = me.phone_number;
    document.getElementById('user-district').textContent = me.address.road_address ?? '';

    // 인증 상태 뱃지
    const certBadge = document.getElementById('cert-badge');
    if (me.cert_flag === 'approved') {
      certBadge.innerHTML = '<span class="badge badge-open">승인 완료</span>';
    } else if (me.cert_flag === 'pending') {
      certBadge.innerHTML = '<span class="badge badge-pending">검토 중</span>';
    } else if (me.cert_flag === 'rejected') {
      certBadge.innerHTML = '<span class="badge badge-cancelled">반려됨</span>';
      if (me.cert_reject_reason) {
        document.getElementById('reject-reason-msg').textContent = me.cert_reject_reason;
        document.getElementById('reject-reason-section').classList.remove('hidden');
      }
    }

    if (me.is_social_login) {
      document.querySelector('.detail-section:has(#password-form)')?.remove();
      document.getElementById('row-email')?.classList.add('hidden');
      document.getElementById('profile-name').innerHTML =
        `${me.name} <span class="badge-kakao">카카오</span>`;
    }
    // 토큰 없거나 만료되면 비밀번호 변경폼 그냥 표시

    // 역할/인증상태 저장 후 서류 슬롯 로드
    currentUserRole = me.user_role;
    currentCertFlag = me.cert_flag;
    if (me.user_role === 'volunteer' || me.user_role === 'guardian') loadStats(me.user_role);
    else document.querySelector('.stats-grid')?.remove();
    await loadDocuments();
  } catch {
    // 토큰 없거나 만료되면 안내 후 로그인 페이지로
    await showResultModal('로그인이 만료됐어요. 다시 로그인해주세요.', 'error');
    window.location.href = '/pages/login.html';
  }
})();

// 비밀번호 변경폼 제출 처리
// password-form 제출되면 이 함수 실행
document.querySelector('#password-form')?.addEventListener('submit', async (e) => {
  e.preventDefault(); // preventDefault: 새로고침 방지, ?: null이면 뒤를 실행하지 않고 pass

  const errorMsg = document.querySelector('#password-error');
  const successMsg = document.querySelector('#password-success');
  errorMsg.classList.add('hidden');
  successMsg.classList.add('hidden');
  // 제출할때마다 이전에 떠있던 알림창 먼저 숨기기

  // 3개의 input 값들
  const currentPassword = document.querySelector('#current-password').value;
  const newPassword = document.querySelector('#new-password').value;
  const newPasswordConfirm = document.querySelector('#new-password-confirm').value;

  // 현재 비밀번호와 새 비밀번호가 같으면 경고 알림창
  if (currentPassword === newPassword) {
    errorMsg.textContent = '새 비밀번호가 현재 비밀번호와 같습니다.';
    errorMsg.classList.remove('hidden');
    return;
  }

  // 새 비밀번호 일치 확인 (클라이언트 검증 = js 브라우저 검증)
  if (newPassword !== newPasswordConfirm) {
    errorMsg.textContent = '새 비밀번호가 일치하지 않습니다.';
    errorMsg.classList.remove('hidden');
    return;  // 함수 즉시 종료
  }

  try {  // api() 호출(jwt 토큰 자동)
    await api('/users/me/password', {
      method: 'PATCH',  // PATCH: 일부 수정(비번 변경처럼 바꿀 필드만 보냄)
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    });

    successMsg.textContent = '비밀번호가 변경되었어요.';
    successMsg.classList.remove('hidden');
    e.target.reset(); // 성공하면 초록알림창과 함께 폼 초기화
  } catch (err) {
    errorMsg.textContent = err.message;
    errorMsg.classList.remove('hidden');
  }  // 실패하면 빨간알림창
});

// 내 정보 수정 모드 진입
function enterEditMode() {
  document.getElementById('input-district').value = document.getElementById('user-district').textContent;

  // span 숨김
  document.getElementById('user-district').classList.add('hidden');

  // input 보임
  document.getElementById('district-edit').style.display = 'flex';

  document.getElementById('btn-edit-info').classList.add('hidden'); // 수정버튼 숨김
  document.getElementById('edit-buttons').style.display = 'flex';   // 저장/취소 버튼 등장
  document.getElementById('btn-save-info').disabled = false;        // 저장 버튼 활성화

  const infoMsg = document.getElementById('info-msg');
  infoMsg.textContent = '';
  infoMsg.className = 'hidden';  // 이전에 남아있던 성공/에러 메시지 초기화
}

// 내 정보 수정 모드 종료(enterEditMode의 반대)
function exitEditMode() {
  document.getElementById('user-district').classList.remove('hidden');
  document.getElementById('district-edit').style.display = 'none';

  document.getElementById('btn-edit-info').classList.remove('hidden');
  document.getElementById('edit-buttons').style.display = 'none';
}

document.querySelector('#btn-edit-info')?.addEventListener('click', enterEditMode);

document.querySelector('#btn-cancel-info')?.addEventListener('click', () => {
  exitEditMode();  // 취소 버튼
  document.getElementById('info-msg').classList.add('hidden');  // 메시지 같이 숨김
});

let mypageAddressData = null;

document.querySelector('#btn-save-info')?.addEventListener('click', async () => {
  const infoMsg = document.getElementById('info-msg');
  const saveBtn = document.getElementById('btn-save-info');

  if (!mypageAddressData) {
    infoMsg.textContent = '주소 검색 버튼으로 주소를 선택해주세요.';
    infoMsg.className = 'alert alert-error';
    return;
  }

  saveBtn.disabled = true;  // api 호출 중 중복 클릭 방지
  try {
    const updated = await api('/users/me', {
      method: 'PATCH',
      body: JSON.stringify({ address: mypageAddressData }),
    });

    // 내 정보 텍스트 갱신
    document.getElementById('user-district').textContent = updated.address.road_address ?? '';

    // 프로필 카드 갱신
    const roleLabel = { volunteer: '봉사자', guardian: '보호자', admin: '관리자' }[updated.user_role] ?? updated.user_role;
    document.getElementById('profile-role-district').textContent = `${roleLabel} · ${updated.address.road_address ?? ''}`;

    exitEditMode();
    infoMsg.textContent = '정보가 수정됐습니다.';
    infoMsg.className = 'alert alert-success';
    setTimeout(() => { infoMsg.classList.add('hidden'); }, 3000);  // 성공 메시지 시간제한
  } catch (err) {
    infoMsg.textContent = err.message || '수정에 실패했습니다. 다시 시도해주세요.';
    infoMsg.className = 'alert alert-error';
    saveBtn.disabled = false;  // 다시 저장 시도 가능
  }
});

// 주소 검색 (register.js와 동일)
document.querySelector('#btn-search-address-mypage')?.addEventListener('click', () => {
  if (!window.daum?.Postcode) {
    showResultModal('주소 검색을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.', 'error');
    return;
  }
  new window.daum.Postcode({
    oncomplete(data) {
      const parts = [data.sido, data.sigungu, data.bname].filter(Boolean);
      document.getElementById('input-district').value = parts.join(' ');
      mypageAddressData = mapKakaoAddressToPayload(data);
    },
  }).open();
});

// 로그아웃 버튼 클릭
document.querySelector('#logout-btn')?.addEventListener('click', () => {
  logout();  // api.js 함수(토큰 삭제후 로그인 이동)
});

// 회원 탈퇴 버튼
document.querySelector('#delete-btn')?.addEventListener('click', () => {
  openConfirmModal({
    title: '회원 탈퇴',
    message: '정말 탈퇴하시겠습니까? 모든 정보가 삭제되며 복구할 수 없습니다.',
    confirmText: '탈퇴',
    cancelText: '취소',
    onConfirm: async () => {
      try {
        await api('/users/me', { method: 'DELETE' });
        logout();
      } catch (err) {
        await showResultModal(err.message, 'error');
      }
    },
  });
});
