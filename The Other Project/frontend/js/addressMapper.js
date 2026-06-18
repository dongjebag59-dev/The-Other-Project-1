// frontend/js/addressMapper.js

function toNullableString(value) {
  if (value == null) {
    return null;
  }

  const trimmedValue = String(value).trim();
  return trimmedValue === '' ? null : trimmedValue;
}

function toRequiredString(value) {
  if (value == null) {
    return '';
  }

  return String(value).trim();
}

function toNullableNumber(value) {
  if (value == null || value === '') {
    return null;
  }

  const numberValue = Number(value);
  return Number.isNaN(numberValue) ? null : numberValue;
}

function toApartmentBoolean(value) {
  if (value === 'Y' || value === true) {
    return true;
  }

  if (value === 'N' || value === false) {
    return false;
  }

  return null;
}

export function createEmptyAddressPayload() {
  return {
    road_address: '',
    jibun_address: null,
    zonecode: null,
    sigungu: '',
    bname: null,
    detail_address: '',
    sido: null,
    building_name: null,
    is_apartment: null,
    lat: null,
    lng: null,
    sigungu_code: null,
  };
}

export function mapKakaoAddressToPayload(kakaoData, coords = null, detailAddress = '') {
  return {
    road_address: toRequiredString(kakaoData.roadAddress),
    jibun_address: toNullableString(kakaoData.jibunAddress),
    zonecode: toNullableString(kakaoData.zonecode),
    sigungu: toRequiredString(kakaoData.sigungu),
    bname: toNullableString(kakaoData.bname),
    detail_address: toRequiredString(detailAddress),
    sido: toNullableString(kakaoData.sido),
    building_name: toNullableString(kakaoData.buildingName),
    is_apartment: toApartmentBoolean(kakaoData.apartment),
    lat: toNullableNumber(coords?.lat),
    lng: toNullableNumber(coords?.lng),
    sigungu_code: toNullableString(kakaoData.sigunguCode),
  };
}


export function mergeDetailAddress(addressPayload, detailAddress = '') {
  return {
    ...addressPayload,
    detail_address: toRequiredString(detailAddress),
  };
}

export function formatAddressPreview(addressPayload) {
  const parts = [
    addressPayload.road_address,
    addressPayload.detail_address,
  ].filter((value) => value && String(value).trim() !== '');

  return parts.join(' ');
}