# SeSAC Cloud/DevOps 과정 프로젝트 및 실습 아카이브

이 저장소는 **SeSAC Cloud/DevOps 과정**에서 수행한 클라우드 인프라 설계, 자동화 배포, 실시간 데이터 수집 및 기계학습 파이프라인 구축 프로젝트의 산출물과 가이드 문서들을 보관하는 공간입니다.

---

## 📂 디렉터리 구성

저장소는 크게 **2차 프로젝트**와 **최종 프로젝트**로 구성되어 있습니다.

```
/Users/beom/workspace/projects/sesac/
├── 2차 프로젝트/             # 쿠버네티스를 활용한 실시간 웹로그 수집 인프라 구축
│   ├── README.md             # 인프라 상세 요구사항 및 트러블슈팅 가이드
│   └── 새싹_4조_2차세미프로젝트_발표자료.pdf
└── 최종 프로젝트/            # E-commerce 코스메틱 상품 개인화 추천 시스템 인프라 구축 (새싹방범대)
    ├── README.md             # 최종 프로젝트 개요 및 산출물 소개
    ├── CCCR_새싹_최종 프로젝트 상장_새싹방범대.pdf
    ├── 새싹 방범대 최종 프로젝트 발표자료.pdf
    └── recommendation-system/ # 실시간 추천 시스템 인프라 및 소스 코드
        ├── README.md         # 서비스 컴포넌트 구성 및 로컬 검증 가이드
        ├── docs/             # 시스템 아키텍처 기술서, 트러블슈팅, 플랫폼 설치 가이드
        └── scripts/          # 로컬 의존성 설치, Kubeflow Manifests EKS 설치 자동화 스크립트
```

---

## 🛠 주요 프로젝트 및 수행 내용

### 1. [2차 프로젝트 (2차 세미 프로젝트)](./2차%20프로젝트)
- **목적**: 회원제 쇼핑몰 비즈니스 요구사항에 맞춰 고가용성 클라우드 인프라를 설계하고, 실시간 사용자 클릭 로그 수집 파이프라인을 연동
- **핵심 인프라 및 기술 스택**:
  - GKE Autopilot 클러스터, Cloud DNS, Cloud Load Balancing (HTTPS 라우팅)
  - GCP Pub/Sub (Ordering Key 및 지수 백오프), Cloud Dataflow, Elastic Cloud (Elasticsearch & Kibana)
  - Jenkins, Docker, GitHub 통합 CI/CD 파이프라인
  - Managed Service for Prometheus, Cloud Operations 통합 모니터링 대시보드
- **상세 설명**: [2차 프로젝트/README.md](./2차%20프로젝트/README.md)

### 2. [최종 프로젝트 - 새싹방범대](./최종%20프로젝트)
- **목적**: AWS 클라우드 상에서 일일 활성 사용자(DAU) 280만 명, 피크 타임 28만 명 규모의 대규모 트래픽 처리가 가능한 화장품 개인화 추천 시스템 인프라 및 E2E 실시간 데이터 수집/전처리 파이프라인 구축
- **핵심 인프라 및 기술 스택**:
  - AWS ECS (Auto Scaling Group), Application Load Balancer, Amazon Aurora DB (Multi-AZ), Amazon ElastiCache (Redis)
  - Amazon Kinesis Data Streams & Firehose (실시간 행동 로그 수집), Amazon S3, AWS Glue (Daily Batch), Amazon Redshift (데이터 웨어하우스)
  - AWS EKS 내 Kubeflow Pipelines를 통한 기계학습 모델(LightFM) 학습 및 Redis 캐시 적재 자동화
  - k6 (부하 테스트), InfluxDB, Grafana 통합 대시보드 모니터링
- **상세 설명**: [최종 프로젝트/README.md](./최종%20프로젝트/README.md) 및 [recommendation-system/README.md](./최종%20프로젝트/recommendation-system/README.md)
