# 밥동무

독거 어르신을 위한 식사 동반 플랫폼 - FastAPI 백엔드

https://babdongmu.duckdns.org/

## 기술 스택

- **Framework**: FastAPI (Python 3.11)
- **Database**: SQLite (로컬) / PostgreSQL (프로덕션), SQLAlchemy 2.x async + Alembic
- **Auth**: JWT (PyJWT + bcrypt)
- **Infra**: Docker, AWS EC2, Caddy, GitHub Actions

## 로컬 실행

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일에서 SECRET_KEY 등 설정
```

### 2-A. pip으로 실행

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2-B. uv로 실행

```bash
uv sync
uv run uvicorn app.main:app --reload
```

### 2-C. Docker로 실행

```bash
docker compose up --build
```

### DB 초기화 동작 방식

| 상황 | 동작 |
|------|------|
| `babdongmu.db` 없음 (최초 실행) | 서버 시작 시 `create_all`로 자동 생성 |
| `babdongmu.db` 있음 + `DEBUG=True` | 서버 시작 시 `alembic upgrade head` 자동 실행 |
| `babdongmu.db` 있음 + `DEBUG=False` | 아무것도 안 함 |
| 프로덕션 (PostgreSQL) | `deploy.yml`에서 `alembic upgrade head` 실행 |

### 모델/DB 스키마가 바뀐 직후 pull 받았을 때

`.env`에 `DEBUG=True`가 설정되어 있으면 서버 시작 시 자동으로 migration이 적용됩니다.

`no such column` 같은 에러가 나거나 DB를 완전히 초기화하고 싶으면:

```bash
# 서버 중지 후
rm babdongmu.db
uvicorn app.main:app --reload  # 자동으로 create_all 실행
```

## API 문서

서버 실행 후 아래 주소에서 Swagger UI 확인:

- http://localhost:8000/docs

## 린터 (Ruff)

코드 품질 유지를 위해 [Ruff](https://docs.astral.sh/ruff/)를 사용합니다. 설정은 `pyproject.toml`에 정의되어 있습니다.

```bash
# 설치
pip install ruff

# 린트 검사
ruff check app/

# 자동 수정
ruff check app/ --fix

# 코드 포맷팅
ruff format app/
```

## 프로젝트 구조

```
app/                             # 백엔드 (FastAPI)
├── main.py                      # FastAPI 앱 진입점
├── config.py                    # 환경변수 설정
├── database.py                  # MongoDB 연결 관리
├── scheduler.py                 # 호스팅 상태 자동 전환 스케줄러
├── core/
│   └── security.py              # JWT + 비밀번호 해싱
├── api/v1/
│   └── router.py                # API 라우터 통합
├── domain/
│   ├── common/
│   │   └── models.py                # Address 공유 모델
│   ├── user/                    # 유저 (봉사자/보호자/관리자)
│   │   ├── models.py                # 유저 문서 스키마
│   │   ├── schemas.py                # 요청/응답 DTO
│   │   ├── router.py                # 인증 API 엔드포인트
│   │   ├── service.py               # 비즈니스 로직
│   │   └── dependency.py            # 인증 의존성
│   ├── senior/                  # 어르신
│   │   ├── models.py                # 어르신 문서 스키마
│   │   ├── schemas.py                # 요청/응답 DTO
│   │   ├── router.py                # 어르신 API 엔드포인트
│   │   └── service.py               # 비즈니스 로직
│   ├── hosting/                 # 호스팅
│   │   ├── models.py                # 호스팅 문서 스키마
│   │   ├── schemas.py                # 요청/응답 DTO
│   │   ├── router.py                # 호스팅 API 엔드포인트
│   │   └── service.py               # 비즈니스 로직
│   ├── match/                   # 매칭
│   │   ├── models.py                # 매칭 문서 스키마
│   │   ├── schemas.py                # 요청/응답 DTO
│   │   ├── router.py                # 매칭 API 엔드포인트
│   │   └── service.py               # 비즈니스 로직
│   ├── review/                  # 후기
│   │   ├── models.py                # 후기 문서 스키마
│   │   ├── schemas.py                # 요청/응답 DTO
│   │   ├── router.py                # 후기 API 엔드포인트
│   │   └── service.py               # 비즈니스 로직
│   ├── admin/                   # 관리자
│   │   ├── router.py                # 관리자 API 엔드포인트
│   │   └── service.py               # 비즈니스 로직
│   └── ai/                      # Gemini AI 소개글
│       └── router.py                # AI 소개글 생성 엔드포인트
└── services/
    ├── sms.py                       # Solapi SMS 발송 유틸리티
    ├── ai.py                        # Gemini 소개글 생성
    ├── qr.py                        # QR 코드 생성
    └── r2.py                        # Cloudflare R2 파일 업로드
frontend/                        # 프론트엔드 (HTML/CSS/JS)
├── index.html                   # 랜딩 페이지
├── css/
│   └── common.css               # 공통 스타일 (DESIGN.md 기반)
├── js/
│   ├── api.js                   # API 공통 헬퍼
│   ├── authGuard.js             # 인증/권한 가드
│   ├── base.js                  # 공통 초기화 (네비게이션 등)
│   ├── addressMapper.js         # 카카오 주소 데이터 매핑
│   ├── login.js                 # 로그인
│   ├── register.js              # 회원가입
│   ├── mypage.js                # 마이페이지
│   └── admin.js                 # 관리자 대시보드
└── pages/
    ├── login.html               # 로그인
    ├── register.html            # 회원가입
    ├── hostings.html            # 호스팅 목록 (보호자)
    ├── hosting-match.html       # 호스팅 목록 (봉사자)
    ├── hosting-detail.html      # 호스팅 상세 (봉사자/보호자)
    ├── my-matches.html          # 내 매칭
    ├── mypage.html              # 마이페이지
    ├── guardian.html            # 보호자 관리
    ├── admin.html               # 관리자 대시보드
    ├── review-detail.html       # 후기 상세
    └── check.html               # QR 체크인/체크아웃
tests/                           # 테스트
├── conftest.py                  # TestClient fixture
└── test_user.py                 # 유저 인증 테스트
```

---

## Git 작업 가이드

### 0. Git 명령어 기본 용어

| 용어 | 의미 | 예시 |
|------|------|------|
| `origin` | GitHub 원격 저장소의 별명 | `origin` = `https://github.com/gabriel-1204/Babdongmu.git` |
| `feature/user` | 내 컴퓨터(로컬)의 브랜치 | `git checkout feature/user` |
| `origin/main` | GitHub(원격)의 main 브랜치 | `git merge origin/main` |

**origin을 붙이는 기준:**
- **내 컴퓨터에서 이동**할 때 → origin 안 붙임 (`git checkout feature/user`)
- **GitHub의 코드를 참조**할 때 → origin 붙임 (`git merge origin/main`, `git push origin 내브랜치`)

자주 쓰는 명령어 정리:

| 명령어 | 하는 일 |
|--------|---------|
| `git fetch origin` | GitHub에서 최신 정보를 가져옴 (내 코드는 안 바뀜) |
| `git merge origin/main` | GitHub의 main 코드를 내 브랜치에 합침 |
| `git checkout 브랜치명` | 다른 브랜치로 이동 |
| `git status` | 변경된 파일 목록 확인 |
| `git add 파일명` | 커밋할 파일을 지정 |
| `git commit -m "메시지"` | 변경사항을 저장 (커밋) |
| `git push origin 브랜치명` | 내 커밋을 GitHub에 업로드 |

### 1. PR 올리기 전 main 최신화 필수

PR을 올리기 전에 반드시 최신 main을 내 브랜치에 반영해야 합니다.

```bash
git fetch origin
git merge origin/main
# 충돌이 있으면 해결 후 커밋
```

### 2. `git add .` 사용 금지

`git add .`이나 `git add -A`를 사용하면 **본인이 수정하지 않은 파일까지 커밋에 포함**됩니다.

#### 올바른 커밋 순서

```bash
# 1단계: 변경된 파일 목록 확인
git status

# 2단계: 본인이 작업한 파일만 골라서 추가
git add app/domain/hosting/service.py
git add app/domain/hosting/router.py

# 3단계: 스테이징된 파일이 내 것만인지 다시 확인
git diff --staged --stat

# 4단계: 커밋
git commit -m "[hosting] 호스팅 신청 서비스 구현"
```

#### 특정 폴더 안의 파일만 추가하고 싶을 때

```bash
# 본인 담당 폴더만 추가
git add app/domain/hosting/
```

#### 실수로 다른 파일까지 add 했을 때

```bash
# 특정 파일을 스테이징에서 제거 (파일 내용은 유지됨)
git restore --staged app/config.py
```

### 3. 공통 파일 수정 시 팀 공유

아래 파일들은 여러 파트에서 사용하므로, 수정 전에 반드시 팀에 알려주세요.

| 공통 파일 | 역할 |
|-----------|------|
| `app/config.py` | 환경변수 설정 |
| `app/database.py` | DB 연결 관리 |
| `app/main.py` | FastAPI 앱 진입점 |
| `app/api/v1/router.py` | API 라우터 통합 |
| `requirements.txt` | 패키지 의존성 |

공통 파일 수정이 필요하면:
1. 팀 채팅에 수정 내용 공유
2. **별도 PR로 먼저 머지**
3. 나머지 팀원이 `git fetch origin && git merge origin/main`으로 반영

### 4. 전체 작업 흐름 요약

```
작업 시작
  └─ git fetch origin && git merge origin/main   (최신화)
  └─ 코드 작업
  └─ git status                                   (변경 파일 확인)
  └─ git add 내파일만                              (본인 파일만 추가)
  └─ git diff --staged --stat                     (스테이징 확인)
  └─ git commit -m "[파트] 작업내용"                (커밋)
  └─ git fetch origin && git merge origin/main    (PR 전 다시 최신화)
  └─ git push origin 내브랜치                      (푸시)
  └─ GitHub에서 PR 생성
```
