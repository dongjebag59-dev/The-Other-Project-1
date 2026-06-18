# 밥동무 데이터베이스 설계

## 기술 스택
- **DB**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.x (asyncio / Mapped 스타일)
- **드라이버**: asyncpg
- **마이그레이션**: Alembic

---

## 마이그레이션 운영 방법

### 모델 변경 후 migration 생성
```bash
alembic revision --autogenerate -m "변경내용_간단히"
alembic upgrade head  # 로컬 반영 (DEBUG=False인 경우)
```

### 자주 쓰는 명령어
| 명령어 | 설명 |
|--------|------|
| `alembic upgrade head` | 최신 migration까지 적용 |
| `alembic downgrade -1` | 한 단계 롤백 |
| `alembic current` | 현재 적용된 migration 확인 |
| `alembic history` | migration 히스토리 조회 |

### 프로덕션 반영
`deploy.yml`에서 서버 시작 전 `alembic upgrade head`가 자동 실행됩니다.

---

## 테이블 목록

| 테이블 | 설명 | ORM 모델 위치 |
|--------|------|---------------|
| `addresses` | 공통 주소 (users / seniors / hostings 1:1 참조) | `app/domain/common/models.py` → `Address` |
| `users` | 회원 (봉사자 / 보호자 / 관리자) | `app/domain/user/models.py` → `User` |
| `documents` | 회원 신원 서류 (봉사자/보호자) | `app/domain/user/models.py` → `Document` |
| `phone_verifications` | SMS 인증 코드 | `app/domain/user/models.py` → `PhoneVerification` |
| `seniors` | 어르신 정보 | `app/domain/senior/models.py` → `Senior` |
| `hostings` | 호스팅 (어르신이 개설하는 밥자리) | `app/domain/hosting/models.py` → `Hosting` |
| `matching_info` | 매칭 신청 정보 | `app/domain/match/models.py` → `MatchingInfo` |
| `reviews` | 후기 | `app/domain/review/models.py` → `Review` |
| `review_img` | 후기 이미지 (최대 5개) | `app/domain/review/models.py` → `ReviewImg` |
| `sms_logs` | SMS 발송 이력 | `app/domain/hosting/models.py` → `SmsLog` |

---

## 테이블 상세

### addresses
| 컬럼 | 타입 | 설명 |
|------|------|------|
| address_id | PK | 주소 ID |
| road_address | VARCHAR | 도로명 주소 |
| jibun_address | VARCHAR nullable | 지번 주소 |
| zonecode | VARCHAR(10) nullable | 우편번호 |
| sigungu | VARCHAR | 시군구 |
| bname | VARCHAR nullable | 법정동/리명 |
| detail_address | VARCHAR | 상세주소 |
| sido | VARCHAR nullable | 시/도 |
| building_name | VARCHAR nullable | 건물명 |
| is_apartment | BOOLEAN nullable | 아파트 여부 |
| lat | FLOAT nullable | 위도 |
| lng | FLOAT nullable | 경도 |
| sigungu_code | VARCHAR(20) nullable | 법정동 코드 (user-hosting 주소 근접 정렬 기준) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

> `users` / `seniors` / `hostings` 각각 1:1 FK로 참조 (`UNIQUE` 제약).  
> 생성: 엔티티보다 먼저 INSERT → `flush()` → 엔티티에 address_id 세팅.  
> 삭제: 엔티티 DELETE → `flush()` → 고아 address row DELETE (서비스 레이어에서 명시적 처리).  
> hosting 주소는 생성 시점 senior 주소의 스냅샷으로 별도 row 유지.

---

### users
| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | PK | 회원 ID |
| kakao_id | VARCHAR(50) unique nullable | 카카오 회원 ID. 일반 회원가입 시 NULL |
| name | VARCHAR | 이름 |
| email | VARCHAR unique nullable | 이메일. 카카오 로그인 시 NULL 가능 |
| password | VARCHAR nullable | 비밀번호 해시. 카카오 로그인 시 NULL |
| phone_number | VARCHAR nullable | 전화번호. 카카오 로그인 시 NULL 가능 |
| address_id | FK → addresses (unique) | 주소 |
| user_role | ENUM | 역할 (`VOLUNTEER` / `GUARDIAN` / `ADMIN`) |
| cert_flag | ENUM | 인증 여부 (`PENDING` / `APPROVED` / `REJECTED`). 기본값 `PENDING` |
| cert_reject_reason | VARCHAR(500) nullable | 서류 반려 사유. 반려 시 입력, 승인 시 NULL |
| created_at | TIMESTAMP | 가입일 |
| updated_at | TIMESTAMP nullable | 수정일 |

> `admin` 계정은 회원가입 API로 생성 불가. seed 스크립트로 별도 생성.  
> ENUM 저장값은 Python `enum.Enum` name 기준 대문자.

---

### documents
| 컬럼 | 타입 | 설명 |
|------|------|------|
| document_id | PK | 서류 ID |
| user_id | FK → users | 회원 |
| document_type | ENUM | 서류 타입 (`CRIMINAL_RECORD` / `WELFARE_CERT` / `FAMILY_CERT` / `IDENTITY_COPY`) |
| document_url | VARCHAR | 서류 파일 URL (Cloudflare R2 저장 후 URL 기록) |
| created_at | TIMESTAMP | 등록일 |
| updated_at | TIMESTAMP nullable | 수정일 |

> 서류 심사 결과는 `users.cert_flag`로 관리. 반려 사유는 `users.cert_reject_reason`에 기록.  
> `CRIMINAL_RECORD`: 봉사자 범죄경력조회서 / `WELFARE_CERT`: 보호자 복지관 인증서류 / `FAMILY_CERT`: 보호자 가족관계증명서 / `IDENTITY_COPY`: 공통 신분증 사본

---

### phone_verifications
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | PK | ID |
| phone_number | VARCHAR(20) index | 인증 대상 전화번호 |
| code | VARCHAR(6) | 인증 코드 |
| expires_at | TIMESTAMP | 만료 시각 |
| is_verified | BOOLEAN | 인증 완료 여부. 기본값 `false` |
| created_at | TIMESTAMP | 생성일 |

---

### seniors
| 컬럼 | 타입 | 설명 |
|------|------|------|
| senior_id | PK | 어르신 ID |
| guardian_id | FK → users | 담당 보호자 |
| address_id | FK → addresses (unique) | 주소 |
| name | VARCHAR | 이름 |
| gender | ENUM | 성별 (`male` / `female` / `other`) |
| birth_date | DATE | 생년월일 (나이는 응답 시점에 계산) |
| special_note | TEXT nullable | 특이사항 (병력, 주의사항) |
| active_flag | BOOLEAN | 활성 상태. 기본값 `true` |
| ai_summary | TEXT nullable | Gemini AI 생성 소개글 |
| max_people | INT | 수용 가능 인원 (호스팅 기본값으로 사용, 최소 2) |
| qr_code | VARCHAR nullable | UUID (어르신 등록 시 자동 생성. 체크인/체크아웃 URL 토큰으로 사용) |
| created_at | TIMESTAMP | 등록일 |
| updated_at | TIMESTAMP | 수정일 |

---

### hostings
| 컬럼 | 타입 | 설명 |
|------|------|------|
| hosting_id | PK | 호스팅 ID |
| senior_id | FK → seniors nullable (SET NULL) | 어르신. senior 삭제 시 NULL로 유지 (이력 보존) |
| address_id | FK → addresses (unique) | 주소 (생성 시점 senior 주소의 스냅샷) |
| menu | VARCHAR | 메뉴 |
| hosting_at | TIMESTAMP | 호스팅 시작 일시 |
| hosting_end | TIMESTAMP | 호스팅 종료 일시 |
| max_people | INT | 모집 가능 인원 (seniors.max_people이 기본값, 수정 가능, 최소 2) |
| hosting_status | ENUM | 모집 상태 (`OPEN` / `FULL` / `FIXED` / `FAILED` / `IN_PROGRESS` / `CLOSED`). 기본값 `OPEN` |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

---

### matching_info
| 컬럼 | 타입 | 설명 |
|------|------|------|
| matching_id | PK | 매칭 ID |
| hosting_id | FK → hostings | 호스팅 |
| vt_id | FK → users | 봉사자 |
| senior_id | FK → seniors | 어르신 |
| match_status | ENUM | 매칭 상태 (`APPROVED` / `CANCELLED` / `NOT_VISITED`). 기본값 `APPROVED` |
| check_in_time | TIMESTAMP nullable | 체크인 시간 |
| check_out_time | TIMESTAMP nullable | 체크아웃 시간 |
| actual_volunteer_time | INT nullable | 실봉사시간 (관리자 최종 부여, 분 단위) |
| created_at | TIMESTAMP | 신청일 |

> UNIQUE INDEX `uix_hosting_vt_active` on (hosting_id, vt_id) — `CANCELLED` 상태 제외하고 중복 신청 방지

---

### reviews
| 컬럼 | 타입 | 설명 |
|------|------|------|
| review_id | PK | 후기 ID |
| matching_id | FK → matching_info (index) | 매칭 정보 |
| vt_id | FK → users (index) | 봉사자 |
| contents | TEXT | 후기 내용 |
| created_at | TIMESTAMP | 작성일 |
| updated_at | TIMESTAMP nullable | 수정일 |

---

### review_img
| 컬럼 | 타입 | 설명 |
|------|------|------|
| image_id | PK | 이미지 ID |
| review_id | FK → reviews (index) | 후기 |
| image_url | VARCHAR | 이미지 URL (Cloudflare R2 저장 후 URL 기록) |
| created_at | TIMESTAMP | 등록일 |

> 후기당 최대 5개

---

### sms_logs
| 컬럼 | 타입 | 설명 |
|------|------|------|
| sms_id | PK | SMS ID |
| hosting_id | FK → hostings | 관련 호스팅 |
| receiver_id | FK → users | 수신자 |
| is_send | BOOLEAN | 발송 성공 여부 |
| alarm_type | ENUM | 알람 구분 (`match` / `checkin` / `checkout` / `update` / `delete`) |
| contents | TEXT | 발송 내용 |
| created_at | TIMESTAMP | 발송일 |

> 수신자가 여러 명인 경우 수신자별로 row 생성 (예: 호스팅 삭제 시 신청한 봉사자 전원)

---

## SMS 발송 트리거

| alarm_type | 발송 시점 | 수신자 |
|------------|-----------|--------|
| `match` | 봉사자가 호스팅 신청 시 | 보호자 |
| `checkin` | 봉사자가 방문 체크인 시 | 보호자 |
| `checkout` | 봉사자가 방문 체크아웃 시 | 보호자 |
| `delete` | 호스팅 삭제 시 | 신청한 봉사자 전원 |
| `update` | (미사용) | 신청한 봉사자 전원 |

---

## 테이블 관계 요약

```
addresses  ─── users       (1:1, 주소)
addresses  ─── seniors     (1:1, 주소)
addresses  ─── hostings    (1:1, 주소)
users      ──< documents
users      ──< seniors     (보호자)
seniors    ──< hostings
hostings   ──< matching_info
users      ──< matching_info (봉사자)
matching_info ──< reviews
users      ──< reviews     (봉사자)
reviews    ──< review_img
hostings   ──< sms_logs
users      ──< sms_logs    (수신자)
```
