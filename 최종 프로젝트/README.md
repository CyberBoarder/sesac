# 최종 프로젝트: E-commerce 코스메틱 상품 개인화 추천 시스템 인프라 구축 (새싹방범대)

본 디렉터리는 SeSAC Cloud/DevOps 과정 최종 프로젝트인 **"새싹방범대"**팀의 시스템 설계 산출물, 발표 자료, 포상 상장 및 전체 소스코드를 포함하고 있습니다.

---

## 📂 구성 파일 및 디렉터리 안내

1. **[recommendation-system/](./recommendation-system)**:
   - 추천 시스템의 백엔드, 프론트엔드, ML 학습 파이프라인(Kubeflow), 데이터 수집(Kinesis) 및 로컬 검증 스크립트가 담긴 소스코드 저장소 루트입니다.
   - 상세 설명: [recommendation-system/README.md](./recommendation-system/README.md)
2. **[CCCR_새싹_최종 프로젝트 상장_새싹방범대.pdf](./CCCR_새싹_최종%20프로젝트%20상장_새싹방범대.pdf)**:
   - 본 프로젝트의 우수성을 인정받아 수상한 최종 프로젝트 최우수상 상장 사본입니다.
3. **[새싹 방범대 최종 프로젝트 발표자료.pdf](./새싹%20방범대%20최종%20프로젝트%20발표자료.pdf)**:
   - 팀 빌딩, 아키텍처 토폴로지, 데이터 흐름, 부하 테스트 결과(k6) 및 최종 시연 내용을 수록한 종합 발표용 슬라이드 문서입니다.

---

## 🏗️ 핵심 시스템 구조 및 기술 명세서

추천 시스템의 주요 구성 요소와 구축 세부 정보는 하위 `recommendation-system/docs` 경로에 작성된 백서에서 상세히 설명하고 있습니다.

* **[아키텍처 구성 기술서](./recommendation-system/docs/architecture.md)**: Route 53, CloudFront, ECS, Aurora MySQL, ElastiCache Redis, Kinesis, S3, Glue, Redshift, Kubeflow, EKS 인프라 및 트래픽 산정 기준 수록
* **[OSS 및 플랫폼 환경 배포 가이드](./recommendation-system/docs/install_oss.md)**: EKS 클러스터 구성, Kustomize 기반 Kubeflow 배포 가이드 및 로컬 모의 컴파일러 런타임 구축 가이드
* **[데브옵스 트러블슈팅 가이드](./recommendation-system/docs/troubleshooting.md)**: Kinesis 샤드 확장 병목 해결, Aurora DB 커넥션 풀링 개선, Kubeflow 파이프라인 캐시 이슈 대응 및 권한 제어 등 직면한 문제들과 그 해결 과정 분석
