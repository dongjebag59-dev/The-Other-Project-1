// favicon
const favicon = document.createElement('link');
favicon.rel = 'icon';
favicon.href = '/assets/icons/favicon.ico';
favicon.type = 'image/x-icon';
document.head.appendChild(favicon);

// ── 내비게이션 ────────────────────────────────────────────

const _NAV_LOGO_SVG = `<svg class="nav-logo-icon" viewBox="0 0 32 32" fill="none">
  <circle cx="16" cy="16" r="14" fill="#D4763C" opacity="0.12"/>
  <path d="M8 18c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="#D4763C" stroke-width="2" stroke-linecap="round"/>
  <path d="M6 18h20v1c0 3.3-2.7 6-6 6h-8c-3.3 0-6-2.7-6-6v-1z" fill="#D4763C" opacity="0.2"/>
  <ellipse cx="16" cy="18" rx="10" ry="2" fill="#D4763C" opacity="0.15"/>
  <path d="M13 14c-.5-2 .5-4 3-4s3.5 2 3 4" stroke="#5B8C5A" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
</svg>`;

const _NAV_LINKS = {
  volunteer: [
    { href: '/pages/hosting-match.html', label: '호스팅 탐색' },
    { href: '/pages/my-matches.html',    label: '내 매칭' },
    { href: '/pages/mypage.html',        label: '마이페이지' },
  ],
  guardian: [
    { href: '/pages/hostings.html',  label: '호스팅' },
    { href: '/pages/guardian.html',  label: '어르신 관리' },
    { href: '/pages/mypage.html',    label: '마이페이지' },
  ],
  admin: [
    { href: '/pages/admin.html',    label: '대시보드' },
    { href: '/pages/stats.html',    label: '통계' },
    { href: '#', label: '로그아웃', onclick: 'logout()' },
  ],
};

const _NAV_LINKS_PUBLIC = [
  { href: '/pages/hosting-match.html', label: '호스팅' },
  { href: '/pages/login.html',         label: '로그인' },
  { href: '/pages/register.html',      label: '회원가입' },
];

function _getNavRole() {
  try {
    const cached = sessionStorage.getItem('cachedUser');
    if (cached) {
      const { user } = JSON.parse(cached);
      if (user?.user_role) return user.user_role;
    }
    const stored = localStorage.getItem('currentUser');
    if (stored) {
      const user = JSON.parse(stored);
      if (user?.user_role) return user.user_role;
    }
  } catch {}
  return null;
}

function _buildNavItems(links, asListItems) {
  const path = window.location.pathname;
  return links.map(link => {
    const isActive = link.href !== '#' && path === link.href;
    const activeAttr = isActive ? ' class="active"' : '';
    const onclickAttr = link.onclick ? ` onclick="${link.onclick}"` : '';
    return asListItems
      ? `<li><a href="${link.href}"${activeAttr}${onclickAttr}>${link.label}</a></li>`
      : `<a href="${link.href}"${activeAttr}${onclickAttr}>${link.label}</a>`;
  }).join('');
}

function loadNav() {
  const role = _getNavRole();
  const links = _NAV_LINKS[role] ?? _NAV_LINKS_PUBLIC;

  const placeholder = document.getElementById('nav-placeholder');
  if (placeholder) {
    placeholder.outerHTML = `<nav class="nav">
  <div class="nav-inner">
    <a href="/" class="nav-logo">${_NAV_LOGO_SVG}밥동무</a>
    <ul class="nav-links">${_buildNavItems(links, true)}</ul>
    <button class="nav-toggle" type="button" onclick="toggleNav()" aria-label="메뉴 열기">
      <span></span><span></span><span></span>
    </button>
  </div>
</nav>
<div class="nav-drawer" id="navDrawer" onclick="closeNav(event)">
  <div class="nav-drawer-content">${_buildNavItems(links, false)}</div>
</div>`;
    return;
  }

  // 재렌더링 — 서버 응답 후 역할이 달라졌을 때 링크만 갱신
  const navLinks = document.querySelector('.nav-links');
  const drawerContent = document.querySelector('.nav-drawer-content');
  if (navLinks) navLinks.innerHTML = _buildNavItems(links, true);
  if (drawerContent) drawerContent.innerHTML = _buildNavItems(links, false);
}

function toggleNav() {
  const toggle = document.querySelector('.nav-toggle');
  const drawer = document.getElementById('navDrawer');
  toggle.classList.toggle('active');
  drawer.classList.toggle('open');
  document.body.style.overflow = drawer.classList.contains('open') ? 'hidden' : '';
}

function closeNav(e) {
  if (e.target === e.currentTarget) toggleNav();
}

// ── 토스트 ────────────────────────────────────────────────

let _toastTimer = null;

function showToast(message, type = '') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `toast show ${type}`.trim();
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { toast.className = 'toast'; }, 3000);
}

loadNav();
