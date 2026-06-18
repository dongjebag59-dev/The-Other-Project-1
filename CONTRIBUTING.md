# 밥동무 코딩 컨벤션

팀원 전원이 지켜야 할 코딩 규칙입니다.

---

## Python (백엔드)

### 네이밍
- 함수 / 변수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`

### 타입 힌트
- 모든 함수의 파라미터와 리턴 타입 필수
- Optional은 `str | None` 형식 사용 (`Optional[str]` 사용 금지)

```python
# Good
async def create_hosting(request: HostingCreateRequest) -> HostingResponse:

# Bad
async def create_hosting(request):
```

### Docstring
- 한글로 작성, 함수 첫 줄에 한 줄 설명

```python
async def create_hosting(request: HostingCreateRequest) -> HostingResponse:
    """호스팅을 생성합니다."""
```

### Import 순서
1. 표준 라이브러리
2. 서드파티 패키지
3. 로컬 모듈

그룹 사이에 빈 줄을 넣습니다.

```python
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.config import settings
```

### 비동기
- 엔드포인트와 서비스 함수는 모두 `async def`

### 에러 처리
- `HTTPException`으로 통일, 상태 코드와 한글 메시지 포함

```python
raise HTTPException(status_code=404, detail="호스팅을 찾을 수 없습니다.")
```

### 린터
- **Ruff** 사용, `ruff check app/` 으로 검사
- 한 줄 최대 100자

---

## JavaScript (프론트엔드)

### 네이밍
- 함수 / 변수: `camelCase`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`

### 스타일
- 문자열: 작은따옴표(`'`) 사용
- 세미콜론: 사용
- 들여쓰기: 스페이스 2칸

### 비동기
- `async/await` 사용 (`.then()` 체이닝 금지)

```javascript
// Good
const data = await api('/hostings');

// Bad
api('/hostings').then(data => { ... });
```

### DOM
- `document.querySelector` / `querySelectorAll` 통일
- `getElementById` 등 혼용 금지

### API 호출
- `frontend/js/api.js`의 `api()` 함수 사용 (JWT 자동 포함)

---

## Git 규칙

### 커밋 메시지
`[파트] 작업내용` 형식

```
[user] 회원가입 서비스 구현
[senior] 어르신 등록 API 완성
[hosting] 호스팅 목록 필터 추가
[match] 체크인/체크아웃 로직 구현
[review] 후기 작성 API 완성
[frontend] 호스팅 목록 페이지 레이아웃
[infra] Docker 설정 수정
```

### 브랜치
- 자기 브랜치에서만 작업
- **main 직접 push 금지**
- PR을 통해서만 main에 머지

### PR
- 최소 **1명 리뷰** 후 머지
- PR 제목도 커밋 메시지와 동일한 형식 사용

### 주석
- 한글로 작성
- "왜" 그렇게 했는지를 설명 (코드가 "무엇"을 하는지는 코드 자체로 표현)

```python
# Good: 이유를 설명
# 이미 매칭된 호스팅에 중복 신청을 방지
if hosting["status"] == "matched":
    raise HTTPException(status_code=400, detail="이미 매칭된 호스팅입니다.")

# Bad: 코드를 그대로 반복
# status가 matched인지 확인
if hosting["status"] == "matched":
```
