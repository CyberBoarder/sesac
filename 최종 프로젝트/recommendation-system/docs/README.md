# 기술 문서 보관소 (docs)

본 디렉터리는 프로젝트의 안정적인 설계 및 원활한 플랫폼 구동을 위해 작성된 상세 기술 설계서 및 운영 문서 보관 공간입니다.

---

## 📄 문서 목록 및 주제

### 1. [시스템 아키텍처 기술서 (architecture.md)](./architecture.md)
* **내용**: 
  - AWS 클라우드 기반의 실시간 데이터 분석 파이프라인 및 백엔드 이중화 토폴로지 분석
  - 쿠팡 페르소나 기준 피크 타임 트래픽(DAU 280만, 피크 타임 28만 동시 접속자) 부하 계산 수치 및 설계 표준 수록
  - 실시간 Kinesis Ingestion 영역과 Glue & Redshift Batch 데이터 가공 흐름 아키텍처 정보 수록

### 2. [오픈소스(OSS) 설치 및 배포 가이드 (install_oss.md)](./install_oss.md)
* **내용**:
  - AWS EKS 환경 기반 Kubeflow 머신러닝 플랫폼 배포 단계별 매뉴얼 (kustomize 및 k8s 리소스 바인딩)
  - 개발자가 배포 과정을 그대로 수행할 수 있도록 명문화된 검증 환경 구축 매니페스트 설명

### 3. [데브옵스 트러블슈팅 가이드 (troubleshooting.md)](./troubleshooting.md)
* **내용**:
  - 실시간 대용량 로그 스트리밍 시 발생한 Kinesis Data Streams 샤드 병목 현상 해결 사례
  - 트래픽 부하 분산 시 Aurora DB 커넥션 과부하 예방을 위한 RDS Proxy 구성 튜닝
  - Kubeflow Pipelines 스케줄러 캐시 리셋 동작 시 발생한 컨테이너 권한 거부 문제 조치 방안 기술

### 4. [기능 명세서 (새싹방범대_기능_명세서_Recommend_System.pdf)](./새싹방범대_기능_명세서_Recommend_System.pdf)
* **내용**:
  - 코스메틱 이커머스 추천 도메인에서의 상세 기능 정의 및 요구사항 매핑
  - 화면 UI 구성(선호도 기반 추천, 카테고리별 클릭 피드백 등) 및 데이터 유효성 검증 규칙 수록
