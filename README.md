# 밥동무 🍚

> 독거 어르신을 위한 식사 동반 매칭 플랫폼

어르신이 식사 자리(호스팅)를 열면 봉사자가 신청해 함께 밥을 먹는 서비스입니다.  
보호자가 어르신을 등록하고 호스팅을 관리하며, 봉사자는 QR 체크인으로 방문을 기록합니다.

**배포 주소:** https://babdongmu.duckdns.org

---

## 목차

- [기술 스택](#기술-스택)
- [서비스 구조](#서비스-구조)
- [주요 기능](#주요-기능)
- [로컬 실행](#로컬-실행)
- [API 문서](#api-문서)
- [프로젝트 구조](#프로젝트-구조)
- [DB 스키마](#db-스키마)
- [외부 서비스](#외부-서비스)

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2.x (async) |
| Database | SQLite (로컬) · PostgreSQL (프로덕션) · Alembic |
| Auth | JWT (PyJWT + bcrypt) · 카카오 OAuth 2.0 |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Infra | Docker · AWS EC2 · Caddy · GitHub Actions |
| Storage | Cloudflare R2 (공개 버킷 + 비공개 버킷) |
| SMS | Solapi (CoolSMS) |
| AI | Google Gemini |

---

## 서비스 구조

```
보호자  ──등록──▶  어르신  ──개설──▶  호스팅
                                      │
봉사자  ──────────────────신청──────▶  매칭
                                      │
                          QR 체크인/체크아웃
                                      │
                          관리자 봉사시간 부여
```

### 역할

| 역할 | 설명 |
|------|------|
| `volunteer` (봉사자) | 호스팅 탐색·신청, QR 체크인/아웃, 후기 작성 |
| `guardian` (보호자) | 어르신 등록·관리, 호스팅 개설·취소 |
| `admin` (관리자) | 신원 서류 승인/반려, 봉사시간 최종 부여, 통계 조회 |

---

## 주요 기능

### 인증
- 이메일/비밀번호 회원가입 + 카카오 OAuth 로그인
- SMS 휴대폰 인증 (회원가입 및 비밀번호 찾기)
- JWT Access Token 기반 인증
- 신원 서류 업로드 (봉사자: 범죄경력조회서 / 보호자: 복지관 인증서류 등)

### 호스팅 상태 머신

```
OPEN ──(정원 마감)──▶ FULL ──(시작 -12h, FULL)──▶ FIXED ──(시작)──▶ IN_PROGRESS ──(종료)──▶ CLOSED
 │                                                    │
 └──────────(시작 -12h, OPEN 또는 시간 초과)──────────▶ FAILED
```

- 호스팅 시작 12시간 전 스케줄러가 자동 전환 + SMS 발송
- 시작 시각: 07:00 이후 (KST) / 종료 시각: 22:00 이전 (KST)
- 진행 시간: 최소 2시간 · 최대 4시간 / 예약 기간: 24시간 ~ 30일 이내

### 매칭
- 선착순 즉시 확정 (`match_status = approved`)
- QR 코드 스캔으로 체크인/체크아웃 기록
- 체크인 시 보호자에게 SMS 자동 발송

### 어르신
- 보호자가 등록, UUID 기반 QR 코드 자동 발급
- 후기 3건 이상 누적 시 Gemini AI가 소개글 자동 생성

### 관리자
- 신원 서류 승인/반려 (반려 사유 저장, 재업로드 시 pending 리셋)
- 체크인/아웃 기록 참고해 봉사시간 직접 입력 (30분 단위 조정)
- 대시보드 통계 조회

---

## 로컬 실행

### 1. 환경 설정

```bash
cp .env.example .env
# .env에서 SECRET_KEY 등 필요한 값 입력
```

### 2-A. uv로 실행 (권장)

```bash
uv sync
uv run uvicorn app.main:app --reload
```

### 2-B. pip으로 실행

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2-C. Docker로 실행

```bash
docker compose up --build
```

### DB 초기화 동작

| 상황 | 동작 |
|------|------|
| DB 파일 없음 (최초 실행) | `create_all`로 자동 생성 |
| DB 있음 + `DEBUG=True` | 서버 시작 시 `alembic upgrade head` 자동 실행 |
| DB 있음 + `DEBUG=False` | 아무것도 안 함 |
| 프로덕션 (PostgreSQL) | `deploy.yml`에서 `alembic upgrade head` 실행 |

DB를 완전히 초기화하고 싶을 때:

```bash
rm babdongmu.db
uvicorn app.main:app --reload
```

### 관리자 계정 생성

```bash
uv run python scripts/create_admin.py
```

---

## API 문서

서버 실행 후 Swagger UI에서 전체 API 확인:

```
http://localhost:8000/docs
```

### 주요 엔드포인트

| 도메인 | 엔드포인트 | 설명 |
|--------|-----------|------|
| 인증 | `POST /api/v1/users/register` | 회원가입 |
| 인증 | `POST /api/v1/users/login` | 로그인 (JWT 발급) |
| 인증 | `GET /api/v1/users/kakao/login` | 카카오 로그인 |
| 어르신 | `POST /api/v1/seniors/` | 어르신 등록 (보호자) |
| 호스팅 | `POST /api/v1/hostings/` | 호스팅 개설 (보호자) |
| 호스팅 | `GET /api/v1/hostings/public` | 호스팅 목록 조회 (봉사자) |
| 매칭 | `POST /api/v1/matches/` | 호스팅 신청 (봉사자) |
| 매칭 | `PATCH /api/v1/matches/{senior_id}/checkin` | QR 체크인 |
| 매칭 | `PATCH /api/v1/matches/{senior_id}/checkout` | QR 체크아웃 |
| 후기 | `POST /api/v1/reviews/` | 후기 작성 |
| 관리자 | `GET /api/v1/admin/users/pending` | 승인 대기 목록 |
| AI | `POST /api/v1/ai/senior/{senior_id}/summary` | AI 소개글 생성 |

---

## 프로젝트 구조

```
app/
├── main.py                  # FastAPI 앱 진입점
├── config.py                # 환경변수 설정
├── database.py              # DB 연결 관리 (async)
├── scheduler.py             # 호스팅 상태 자동 전환 스케줄러
├── core/
│   ├── security.py          # JWT 생성/검증, 비밀번호 해싱
│   └── rate_limit.py        # 인메모리 Rate Limiter
├── api/v1/
│   └── router.py            # 전체 라우터 통합
├── domain/
│   ├── user/                # 회원 (인증, 서류, 마이페이지)
│   ├── senior/              # 어르신
│   ├── hosting/             # 호스팅
│   ├── match/               # 매칭 (체크인/아웃 포함)
│   ├── review/              # 후기
│   ├── admin/               # 관리자
│   ├── ai/                  # Gemini AI 소개글
│   └── common/              # 공유 모델 (Address)
└── services/
    ├── sms.py               # Solapi SMS 발송
    ├── ai.py                # Gemini 소개글 생성
    ├── qr.py                # QR 코드 생성
    └── r2.py                # Cloudflare R2 파일 업로드

frontend/
├── index.html               # 랜딩 페이지
├── css/common.css
├── js/
│   ├── api.js               # API 공통 헬퍼
│   ├── authGuard.js         # 인증/권한 가드
│   └── ...
└── pages/                   # 각 페이지 HTML

alembic/                     # DB 마이그레이션
tests/                       # pytest 테스트
scripts/                     # 유틸리티 스크립트
```

---

## DB 스키마

```
addresses ◀─── users ──▶ documents
              │
              ▼
           seniors ──▶ hostings ──▶ matching_info
                           │               │
                        sms_logs      reviews ──▶ review_imgs
```

ERD 상세: [docs/bab_donmu_erd.html](docs/bab_donmu_erd.html)

---

## 외부 서비스

| 서비스 | 용도 | 환경변수 |
|--------|------|---------|
| Solapi | SMS 발송 | `SOLAPI_API_KEY`, `SOLAPI_API_SECRET`, `SOLAPI_SENDER` |
| Google Gemini | 어르신 소개글 자동 생성 | `GEMINI_API_KEY` |
| Cloudflare R2 | 파일 저장 (후기 이미지 / 신원 서류) | `R2_*` |
| 카카오 OAuth | 소셜 로그인 | `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET` |

R2 버킷 구성:
- `babdongmu-public` — 후기 이미지 (공개, CDN URL)
- `babdongmu-private` — 신원 서류 (비공개, Presigned URL 5분 유효)

---

## 린터 (Ruff)

```bash
ruff check app/        # 린트 검사
ruff check app/ --fix  # 자동 수정
ruff format app/       # 코드 포맷팅
```
