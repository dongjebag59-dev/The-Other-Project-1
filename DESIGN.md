# Design System — 밥동무

## Product Context
- **What this is:** 독거 어르신을 위한 식사 동반 플랫폼. 어르신이 호스트가 되어 봉사자와 함께 식사.
- **Who it's for:** 독거 어르신(60+), 봉사자(20-30대), 보호자(가족), 관리자
- **Space/industry:** 소셜벤처 / 시니어케어 / 봉사 매칭
- **Project type:** 웹앱 (모바일 반응형)

## Aesthetic Direction
- **Direction:** Organic/Warm
- **Decoration level:** Intentional (은은한 텍스처, 따뜻한 배경 톤)
- **Mood:** 집에 초대받은 느낌. 복지 서비스의 차가운 임상적 느낌이 아닌, 따뜻한 밥상 위의 수저 같은 정겨움.

## Typography
- **Display/Hero:** Gmarket Sans Bold — 친근하면서 개성 있는 한국어 서체. 무료.
- **Body:** Pretendard Variable — 한국 웹 가독성 최고. 모든 기기에서 안정적. 무료.
- **UI/Labels:** Pretendard Variable (same as body)
- **Data/Tables:** Pretendard Variable (tabular-nums) — 숫자 정렬이 깔끔함.
- **Code:** JetBrains Mono
- **Loading:**
  - Pretendard: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css`
  - Gmarket Sans: `https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansBold.woff2`
- **Scale:**
  - xs: 12px — 캡션, 메타데이터
  - sm: 14px — 보조 텍스트, 라벨
  - base: 16px — 본문
  - lg: 18px — 강조 본문
  - xl: 24px — 섹션 타이틀
  - 2xl: 36px — 페이지 타이틀
  - 3xl: 48px — 히어로 헤딩

## Color
- **Approach:** Restrained (1 accent + warm neutrals)
- **Primary:** #D4763C — 따뜻한 테라코타. 밥상, 된장찌개의 색. 식욕과 따뜻함.
- **Primary hover:** #C0682F
- **Secondary:** #5B8C5A — 차분한 녹색. 반찬, 채소, 건강, 자연.
- **Secondary hover:** #4D7A4C
- **Background:** #FBF7F2 — 따뜻한 아이보리/크림. 차가운 #FFF 대신 집 느낌.
- **Surface:** #FFFFFF — 카드, 패널, 모달
- **Text:** #2C2420 — 따뜻한 다크 브라운
- **Muted:** #8C7E73 — 따뜻한 회색 (보조 텍스트, 플레이스홀더)
- **Border:** #E8E0D8 — 따뜻한 경계선
- **Semantic:**
  - Success: #5B8C5A (secondary와 동일)
  - Warning: #D4A63C
  - Error: #C94C4C
  - Info: #4C7EC9
- **Dark mode strategy:**
  - Background: #1A1614
  - Surface: #2C2420
  - Primary: #E8935A (밝기 올림)
  - Text: #F0E8E0
  - Muted: #9C8E83
  - Border: #3C3430
  - Semantic alert 배경: 채도 낮추고 어둡게

## Spacing
- **Base unit:** 8px
- **Density:** Comfortable (시니어 친화적 여유 있는 간격)
- **Scale:** xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64)

## Layout
- **Approach:** Grid-disciplined
- **Grid:** mobile 1col, tablet 2col, desktop 3col (카드 그리드)
- **Max content width:** 960px
- **Border radius:**
  - sm: 4px (인풋, 작은 요소)
  - md: 8px (버튼, 알림, 스와치)
  - lg: 12px (카드)
  - xl: 16px (큰 패널)
  - full: 9999px (뱃지, 아바타)

## Motion
- **Approach:** Minimal-functional
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(50-100ms) short(150-250ms) medium(250-400ms) long(400-700ms)
- **사용처:** 페이지 전환, 카드 호버 그림자, 체크인/아웃 성공 피드백, 알림 등장

## Component Patterns

### 호스팅 카드
- 아바타(이름 첫 글자, primary→secondary 그라데이션) + 이름 + 동네
- 오늘의 메뉴 (primary 색, 굵게)
- 날짜/시간 + 상태 뱃지 (모집중/매칭완료)

### 뱃지
- 모집중: 연녹색 배경 #EDF5ED, 텍스트 #3A6B39
- 매칭완료: 연노랑 배경 #FDF5E6, 텍스트 #8B6914
- 완료: 연회색 배경 #F0EBE6, 텍스트 #6B5E53

### 알림 메시지
- 밥동무 톤의 따뜻한 카피 사용
- 성공: "매칭이 확정되었어요!"
- 빈 상태: "아직 활동이 없어요. 첫 밥동무를 시작해보세요!"
- 에러: "이미 다른 분이 신청한 호스팅이에요."

### 버튼
- Primary: 테라코타 배경 + 흰 텍스트
- Secondary: 녹색 배경 + 흰 텍스트
- Ghost: 테라코타 테두리 + 테라코타 텍스트 (호버 시 반전)

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Initial design system created | /design-consultation. "따뜻한 밥상" 컨셉. 복지 서비스의 임상적 파란색 대신 테라코타+크림으로 차별화. |
| 2026-03-30 | Gmarket Sans for display | 한국어 친근함 + 개성. 무료. 복지 서비스의 딱딱한 고딕 대신 따뜻한 인상. |
| 2026-03-30 | Pretendard for body | 한국 웹 가독성 최고. 모든 기기에서 안정적. CDN 무료 배포. |
| 2026-03-30 | Cream background #FBF7F2 | 순백(#FFF) 대신 따뜻한 아이보리로 "집에 온 느낌" 연출. |
