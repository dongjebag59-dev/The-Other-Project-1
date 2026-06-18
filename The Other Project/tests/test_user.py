"""유저 인증 테스트."""


def test_register_returns_501(client):
    """회원가입 엔드포인트가 501을 반환합니다 (미구현)."""
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "test@example.com",
            "password": "test1234",
            "name": "테스트",
            "phone": "010-1234-5678",
            "role": "volunteer",
            "district": "서울시 성북구 정릉동",
        },
    )
    assert response.status_code == 501


def test_login_returns_501(client):
    """로그인 엔드포인트가 501을 반환합니다 (미구현)."""
    response = client.post(
        "/api/v1/users/login",
        json={
            "email": "test@example.com",
            "password": "test1234",
        },
    )
    assert response.status_code == 501
