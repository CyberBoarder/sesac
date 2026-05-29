# 자동화 및 검증 스크립트 (scripts)

본 디렉터리는 프로젝트 빌드, 오픈소스 플랫폼 구성, 데이터 ETL(추출/변환/적재), 부하 테스트 및 로컬 환경 검증을 위한 자동화 스크립트 모음입니다.

---

## 📂 스크립트 목록 및 역할

### 1. 환경 설치 및 인프라 프로비저닝
* **[install_local_deps.sh](./install_local_deps.sh)**: macOS 및 Linux 개발 환경용 로컬 컴파일러와 필수 의존 패키지들을 자동 설치하는 스크립트입니다.
* **[install_kubeflow_manifests.sh](./install_kubeflow_manifests.sh)**: AWS EKS 상에 Kubeflow 플랫폼(v1.7.0 등)을 kustomize 기반으로 배포하기 위한 설치 자동화 스크립트입니다.

### 2. CI/CD 파이프라인 설정
* **[buildspec.yml](./buildspec.yml)**: AWS CodePipeline & CodeBuild를 활용한 메인 배포 파이프라인 빌드/배포 스펙 정의 파일입니다.
* **[buildspec-test.yml](./buildspec-test.yml)**: CI 단계에서 자동화 테스트 및 정적 분석을 수행하기 위한 전용 빌드 스펙 정의 파일입니다.

### 3. 데이터 ETL 및 모델 학습
* **[glue_etl.py](./glue_etl.py)**: S3에 실시간으로 수집 및 축적된 JSON 포맷의 원시 행동 로그를 읽어와 일자별/이벤트별로 파싱한 후 데이터 웨어하우스(Amazon Redshift)에 적재하는 AWS Glue PySpark 배치 작업 스크립트입니다.
* **[train_recommendation.py](./train_recommendation.py)**: Redshift에서 정제된 사용자 평점 및 구매 데이터를 수집하여 LightFM 머신러닝 알고리즘 기반으로 개인화 추천 모델을 학습하는 훈련 스크립트입니다.

### 4. 로컬 모의 환경 및 검증
* **[docker-compose-local.yml](./docker-compose-local.yml)**: 로컬 검증 및 디버깅을 위해 PostgreSQL(DB 역할)과 Redis(추천 데이터 캐시 역할) 모의 컨테이너를 구동하는 Docker Compose 설정 파일입니다.
* **[test_local_pipeline.py](./test_local_pipeline.py)**: 로컬 Docker Compose DB에 목업(Mock) 데이터를 Seeding하고, 추천 모델 학습을 실행한 후 최종 결과물이 Redis에 동기화되는 전 과정을 단 한 번에 검증할 수 있는 E2E 파이프라인 통합 테스트 스크립트입니다.

### 5. 부하 테스트
* **[k6_load_test.js](./k6_load_test.js)**: 웹 애플리케이션의 성능 한계를 검증하기 위해 초당 대규모 동시 요청(TPS)을 가상으로 생성하고, 클릭 로그 데이터 파이프라인의 처리 한계를 측정하는 k6 로드 테스트 스크립트입니다.
