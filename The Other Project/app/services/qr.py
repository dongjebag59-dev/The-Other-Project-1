"""QR 코드 생성 유틸리티."""

import io

import qrcode

from app.config import settings


def build_checkin_url(qr_uuid: str) -> str:
    """QR UUID로 체크인 페이지 URL을 생성합니다."""
    return f"{settings.FRONTEND_BASE_URL}/pages/check.html?qr_uuid={qr_uuid}"


def generate_qr_image(data: str) -> bytes:
    """데이터를 QR 코드 PNG 이미지로 변환하여 반환합니다."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
