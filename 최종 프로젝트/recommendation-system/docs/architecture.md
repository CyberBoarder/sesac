# 시스템 아키텍처 기술서 (System Architecture Whitepaper)

본 문서는 **새싹 방범대** 프로젝트의 각 인프라 컴포넌트 설계와 데이터 수집 및 머신러닝 학습 모델 배포 흐름에 관한 상세 기술 명세서입니다.

![새싹 최종 아키텍처](../original_assets/새싹%20최종%20아키텍처.png)

---

## 1. 인프라 설계 및 백엔드 서비스

### 1-1. 웹 & 애플리케이션 계층 (Web/App Layer)
* **AWS Route 53 & ACM**: 도메인을 등록하고 SSL/TLS 인증서를 적용하여 모든 엔드포인트를 HTTPS(`port 443`)로 제공합니다.
* **AWS CloudFront**: 코스매틱 이미지 및 정적 자산(CSS, JS)의 CDN 배포를 지원하여 지연 속도를 최소화합니다.
* **Application Load Balancer (ALB)**: 두 개의 가용영역(AZ)에 수평 분산된 ECS 컨테이너 타겟그룹으로 트래픽을 로드밸런싱합니다.
* **Amazon ECS (AWS Fargate)**: Spring Boot 기반의 백엔드 서비스를 Auto Scaling Group(ASG)을 통해 트래픽 부하에 따라 유연하게 스케일 아웃합니다.

### 1-2. 데이터베이스 계층 (Database Layer)
* **Amazon Aurora MySQL (Multi-AZ)**:
  - **Master DB**와 **Standby DB**로 구성하여 Master 장애 시 수 초 이내에 Standby로 Failover되도록 고가용성을 확보합니다.
  - 이중화를 통해 데이터 유실을 방지하고 가동성을 99.99% 수준으로 보장합니다.
* **AWS RDS Proxy**:
  - 급격한 사용자 증가(피크 트래픽)로 인한 Connection Pool 고갈 문제를 예방하기 위해 커넥션 풀을 풀링 및 공유합니다.
  - 애플리케이션 인스턴스가 동적으로 스케일링될 때 발생하는 오버헤드를 경감합니다.
* **Amazon ElastiCache (Redis)**:
  - 사용자 세션 데이터와 머신러닝 모델이 추론한 **개인화 추천 상품 ID 리스트(Top-5)**를 캐싱합니다.
  - 상품 상세 페이지 접속 시 DB 쿼리 없이 밀리초(ms) 단위의 초고속 추천 목록 조회를 실현합니다.

---

## 2. 데이터 수집 & ETL 파이프라인

```
[사용자 행동]
   │ (Detail, Cart, Purchase, Rating)
   ▼
[ECS Application]
   │ (Kinesis SDK)
   ▼
[Amazon Kinesis Data Streams]
   │ (실시간 스트림 전달)
   ▼
[Amazon Kinesis Data Firehose]
   │ (파티셔닝 키: event_type)
   ▼
[Amazon S3 (Raw Log Bucket)]  <--- 일자별 파티셔닝 구조로 저장
   │
   │ (Daily 01:00 AM Glue Spark Job 실행)
   ▼
[AWS Glue ETL Job]            <--- 평점 4점 이상 필터링 & 가중치 점수 변환
   │
   ▼
[Amazon Redshift Cluster]     <--- DW에 가중치 매트릭스 테이블 생성
```

### 2-1. 실시간 데이터 수집 (Ingestion)
사용자가 로그인, 클릭, 장바구니 추가, 구매, 평점 남기기 등의 액션을 취하면 백엔드 애플리케이션에서 즉시 JSON 로그를 **Kinesis Data Streams**로 전송합니다.
* **Kinesis Data Firehose**를 연계하여 실시간 버퍼링 후 **Amazon S3** 버킷에 저장합니다.
* 파티셔닝 정책: S3 저장 시 데이터 전처리 속도 향상을 위해 `"Event_type"` 및 날짜(yyyy/mm/dd) 기준으로 버킷 경로를 파티셔닝하여 저장합니다.

### 2-2. 일배치 변환 (ETL) 및 적재 (Load)
* **AWS Glue**: 매일 오전 1시(01:00 AM) 스케줄러에 의해 PySpark 배치 작업이 트리거됩니다.
* **데이터 정제 규칙**:
  - S3에 적재된 로그 데이터를 읽어 정규화합니다.
  - 평점 이벤트(`review_rating`)의 경우, **평점 4점 이상의 신뢰할 수 있는 데이터만 필터링**하여 최종 데이터셋에 포함시킵니다.
  - 각 `event_type`에 가중치(Interaction Score)를 매겨 사용자의 아이템 선호 강도를 수치화합니다.
    - `product_click` = 1점
    - `to_cart` = 2점
    - `purchase` = 3점
    - `review_rating` (>=4점) = 5점
* **Amazon Redshift**: 변환 완료된 사용자-상품 상호작용 매트릭스(User-Item Interaction Matrix)는 대용량 분석에 특화된 Redshift DW 클러스터의 타겟 테이블에 적재됩니다.

---

## 3. Kubeflow 기반 모델 파이프라인

### 3-1. 모델 파이프라인 및 Kubeflow 아키텍처
* **Kubeflow Pipelines (KFP)**: EKS 클러스터상에 구축되어 데이터 로드, 전처리, 모델 학습, 예측 생성, Redis 적재까지의 전 과정을 DAG(Directed Acyclic Graph) 파이프라인으로 제어합니다.
* **Dex & OIDC 연동**: Kubeflow 대시보드에 대한 안전한 사용자 접근 통제를 제공합니다.

### 3-2. 추천 알고리즘 및 예측
* **알고리즘**: Matrix Factorization 및 Collaborative Filtering을 지원하는 **LightFM** 모델을 사용합니다.
* **특징**: 코스매틱 상품 특성상 콜드 스타트(Cold Start) 문제를 해결하기 위해 사용자의 피부 타입 정보 및 상품 카테고리 메타데이터를 하이브리드 형태로 주입해 학습합니다.
* **Daily 배치 예측**:
  - 매일 아침 전처리된 상호작용 테이블을 Redshift에서 로드하여 LightFM 모델을 재학습시킵니다.
  - 각 사용자 ID별로 가장 선호도가 높을 것으로 추정되는 **Top-5 코스매틱 상품 ID 목록**을 생성합니다.
  - 생성된 추천 결과를 `ElastiCache (Redis)` 캐시 서버에 즉시 동기화(Upsert)하여 백엔드 서비스가 0.1초 미만의 속도로 사용자에게 조회할 수 있도록 서빙 구조를 최적화합니다.
