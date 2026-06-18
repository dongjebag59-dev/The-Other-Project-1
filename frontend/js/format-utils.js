/**
 * format-utils.js
 * 여러 파일에서 공통으로 사용하는 포맷·파싱·검증 유틸 모음
 *
 * 포함 항목:
 *   - KST_TIME_ZONE    : 한국 타임존 상수 (Asia/Seoul 하드코딩 방지)
 *   - parseApiDateTime : API 응답 ISO 날짜 문자열 → Date 객체 파싱
 *                        (타임존 정보 없는 문자열은 UTC로 정규화)
 *   - normalizePhone   : 전화번호 정규화 및 유효성 검증 (010+8자리)
 *   - escapeHtml       : innerHTML 삽입 시 XSS 방지용 HTML 이스케이프
 *   - formatDate       : ISO 날짜 → "5월 8일" 형식
 *   - formatDatetime   : ISO 날짜 → "5. 8. 오후 2:30" 형식
 */

export const KST_TIME_ZONE = 'Asia/Seoul';

// API 날짜 문자열을 Date 객체로 변환
// 타임존 정보(Z, +09:00)가 없는 ISO 문자열은 UTC로 간주해 정규화
export function parseApiDateTime(value) {
  if (!value) {
    return null;
  }

  if (value instanceof Date) {
    return value;
  }

  if (typeof value === 'string') {
    const normalizedValue = value.includes('T')
      && !value.endsWith('Z')
      && !/[+-]\d{2}:\d{2}$/.test(value)
      ? `${value}Z`
      : value;

    return new Date(normalizedValue);
  }

  return new Date(value);
}

// 하이픈·공백 제거 후 010+8자리 검증, 유효하지 않은 형식은 null
export function normalizePhone(raw) {
  const digits = raw.trim().replace(/[-\s]/g, '');
  return /^010\d{8}$/.test(digits) ? digits : null;
}

// innerHTML 삽입 전 특수문자 이스케이프 — XSS 방지
export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// ISO 날짜 → "5월 8일" (관리자 대시보드 서류 날짜 등)
export function formatDate(iso) {
  if (!iso) return '-';
  return parseApiDateTime(iso).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
}

// ISO 날짜 → "5. 8. 오후 2:30" (매칭/SMS 등 시각 포함 표시)
export function formatDatetime(iso) {
  if (!iso) return '-';
  return parseApiDateTime(iso).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
