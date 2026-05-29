import http from 'k6/http';
import { sleep, check } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// 커스텀 메트릭 정의
export const recommendationClickCounter = new Counter('recommendation_clicks');
export const recommendationLoadTime = new Trend('recommendation_load_time');

// 부하 테스트 시나리오 구성 (Notion & PDF 발표자료 기반)
// 가상의 사용자 수와 램프업 단계를 정의하여 점진적 부하 증가 테스트 진행
export const options = {
  stages: [
    { duration: '1m', target: 50 },  // 1분 동안 VU 0에서 50으로 램프업
    { duration: '3m', target: 100 }, // 3분 동안 VU 100 유지
    { duration: '1m', target: 0 },   // 1분 동안 VU 100에서 0으로 램프다운
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95%의 요청은 500ms 미만이어야 함
    http_req_failed: ['rate<0.01'],    // 에러율은 1% 미만이어야 함
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

export default function () {
  // 임의의 유저 ID 및 상품 ID 생성 (Notion 명세 기준 풀백 범위)
  const userId = `user${String(Math.floor(Math.random() * 943) + 1).padStart(4, '0')}`;
  const randomProdId = `prod${String(Math.floor(Math.random() * 1682) + 1).padStart(4, '0')}`;

  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': userId,
  };

  // 1. 메인 페이지 방문
  let res = http.get(`${BASE_URL}/`, { headers });
  check(res, { 'main status is 200': (r) => r.status === 200 });
  sleep(1);

  // 2. 상품 상세 페이지 조회 (상세 페이지에서 추천 리스트 로드)
  res = http.get(`${BASE_URL}/product/${randomProdId}`, { headers });
  check(res, { 'product detail status is 200': (r) => r.status === 200 });
  
  // 추천 시스템 서빙 속도 측정 기록
  if (res.json && res.json('rec_prod_list')) {
    recommendationLoadTime.add(res.timings.duration);
  }
  sleep(2);

  // 3. 추천 상품 리스트 중 하나를 클릭하는 행동 모사 (CTR 추적)
  const isRecommendationClick = Math.random() < 0.3; // 30% 확률로 추천 상품 클릭
  if (isRecommendationClick) {
    recommendationClickCounter.add(1);
    const mockRecProdId = `prod${String(Math.floor(Math.random() * 100) + 1).padStart(4, '0')}`;
    
    // rec_click 이벤트 로그 전송
    res = http.post(`${BASE_URL}/api/logs`, JSON.stringify({
      timestamp: new Date().toISOString(),
      user_id: userId,
      event_type: 'rec_click',
      product_id: mockRecProdId,
      page: 'prod_detail',
      rec_prod_list: [mockRecProdId]
    }), { headers });
    
    check(res, { 'log rec_click status is 200': (r) => r.status === 200 });
    sleep(1.5);
  }

  // 4. 장바구니 담기 (to_cart)
  if (Math.random() < 0.4) {
    res = http.post(`${BASE_URL}/api/logs`, JSON.stringify({
      timestamp: new Date().toISOString(),
      user_id: userId,
      event_type: 'to_cart',
      product_id: randomProdId,
      page: 'prod_detail'
    }), { headers });
    check(res, { 'log to_cart status is 200': (r) => r.status === 200 });
    sleep(1);
  }

  // 5. 구매 완료 (purchase)
  if (Math.random() < 0.15) {
    res = http.post(`${BASE_URL}/api/logs`, JSON.stringify({
      timestamp: new Date().toISOString(),
      user_id: userId,
      event_type: 'purchase',
      page: 'cart',
      pur_list: [randomProdId],
      pur_amount: 10000
    }), { headers });
    check(res, { 'log purchase status is 200': (r) => r.status === 200 });
    sleep(1);
  }
}
