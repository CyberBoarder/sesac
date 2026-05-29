# OSS 설치 및 플랫폼 환경 구축 가이드 (OSS Installation Guide)

본 문서는 **새싹 방범대** 프로젝트의 빌드, 배포 및 구동에 필요한 오픈소스 소프트웨어(OSS)들의 설치 과정과 설정 방법을 다루는 종합 가이드라인입니다.

---

## 1. 로컬 개발 환경 및 Python ML 패키지 설치

`scipy`와 `lightfm`은 C/C++ 컴파일 모듈을 포함하고 있어, macOS나 Linux 환경에서 설치 시 컴파일러 오류가 자주 발생합니다. 아래 과정을 따라 시스템 컴파일러 환경을 먼저 세팅한 후 설치해야 합니다.

### 1-1. 시스템 의존성 설치
* **macOS (Apple Silicon 포함)**:
  Xcode Command Line Tools 및 Homebrew를 설치한 후 C/C++ 컴파일러와 PostgreSQL 개발 헤더 라이브러리를 설치합니다.
  ```bash
  # 컴파일 도구 및 라이브러리 설치
  xcode-select --install
  brew install gcc llvm libpq redis
  ```

* **Linux (Ubuntu / Debian 계열)**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y build-essential gcc g++ gfortran python3-dev libpq-dev redis-tools
  ```

### 1-2. Python 가상환경 구성 및 컴파일 플래그 설정
LightFM은 설치 시점에 **numpy의 헤더 파일**이 존재해야 성공적으로 컴파일되므로, 가상환경 활성화 후 `numpy`를 먼저 빌드해야 합니다.

* **macOS Apple Silicon (M1/M2/M3) 환경의 Clang 컴파일러 대응**:
  ```bash
  # 가상환경 생성 및 활성화
  python3 -m venv .venv
  source .venv/bin/activate

  # pip 최신화 및 컴파일용 numpy 선설치
  pip install --upgrade pip setuptools wheel
  pip install numpy>=1.22.0

  # macOS Clang 전용 컴파일러 플래그 주입 후 LightFM 설치
  export LDFLAGS="-L$(brew --prefix)/opt/libpq/lib"
  export CPPFLAGS="-I$(brew --prefix)/opt/libpq/include"
  
  # LightFM C-Extension 컴파일 및 관련 의존성 패키지 설치
  pip install lightfm>=1.16 scipy>=1.8.0 psycopg2-binary>=2.9.0 redis>=5.0.0 pandas>=1.4.0
  ```

---

## 2. AWS EKS 및 Kubeflow 플랫폼 설치 (EKS/Kubeflow v1.8.0)

EKS 환경에 머신러닝 워크플로우 엔진인 **Kubeflow**를 배포하고 외부 인증을 통합합니다.

### 2-1. EKS 클러스터 생성
`eksctl`을 사용하여 Kubeflow 배포에 적합한 노드 사양(CPU/Memory 충분 확보)의 EKS 클러스터를 생성합니다.
```bash
eksctl create cluster \
  --name sesac-ml-cluster \
  --region ap-northeast-2 \
  --version 1.28 \
  --nodegroup-name ml-nodes \
  --node-type m5.xlarge \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed
```

### 2-2. Kustomize 및 Kubeflow Manifests 설치
Kubeflow v1.8.0 설치를 위해서는 반드시 호환되는 **Kustomize v5.0.3** 버전이 필요합니다.
```bash
# Kustomize v5.0.3 다운로드 및 설치
curl -LO https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv5.0.3/kustomize_v5.0.3_darwin_arm64.tar.gz  # macOS arm64
# Linux x86_64의 경우: kustomize_v5.0.3_linux_amd64.tar.gz 사용
tar -zxvf kustomize_v5.0.3_*.tar.gz
sudo mv kustomize /usr/local/bin/

# Kubeflow Manifests 레포지토리 복제
git clone https://github.com/kubeflow/manifests.git -b v1.8.0
cd manifests
```

### 2-3. 단일 명령어 기반 전체 Manifest 빌드 및 설치
CRD(Custom Resource Definition)와 컨트롤러 간의 의존성 경합을 줄이기 위해 순차적으로 배포를 전개합니다:
```bash
# 1단계: 네임스페이스 및 Istio/Cert-Manager 기본 리소스 배포
while ! kustomize build common/cert-manager/cert-manager/base | kubectl apply -f -; do echo "Retrying cert-manager..."; sleep 10; done
while ! kustomize build common/istio-ca/base | kubectl apply -f -; do echo "Retrying istio-ca..."; sleep 5; done
while ! kustomize build common/istio/istio-install/base | kubectl apply -f -; do echo "Retrying istio..."; sleep 5; done

# 2단계: Dex 및 Auth-Service 배포 (OAuth2 연동용)
kustomize build common/dex/overlays/oauth2-proxy | kubectl apply -f -

# 3단계: Kubeflow 핵심 파이프라인 컴포넌트(KFP) 및 대시보드 전체 배포
kustomize build apps/pipeline/upstream/env/cert-manager/platform-agnostic-multi-user | kubectl apply -f -
kustomize build apps/profiles/upstream/overlays/kubeflow | kubectl apply -f -
kustomize build apps/centraldashboard/upstream/overlays/istio | kubectl apply -f -
```

### 2-4. Dex OIDC 설정 변경 (로그인 인증 및 외부 접속 허용)
외부 로드밸런서(ALB) 도메인을 통해 로그인 창으로 정상 리다이렉션되도록 Dex 설정을 패치합니다.
```bash
# dex ConfigMap 수정
kubectl edit configmap dex -n auth
```
`config.yaml` 필드 내 `staticClients` 설정을 외부 도메인에 매핑합니다:
```yaml
staticClients:
- id: kubeflow-oidc-authservice
  redirectURIs:
  - 'https://<EXTERNAL-ALB-DOMAIN>/login'
  name: 'Kubeflow OIDC'
  secret: <secure-generated-client-secret>
```
수정 후 컴포넌트를 재기동합니다:
```bash
kubectl rollout restart deployment dex -n auth
kubectl rollout restart statefulset oidc-authservice -n kubeflow
```

---

## 3. 데이터베이스 및 캐시 서버 (Redis/PostgreSQL) 구축

### 3-1. 로컬 검증 환경 (Docker 기반)
로컬에서 AWS Redshift 및 ElastiCache 서비스 없이 파이프라인 코드를 모의 테스트하려면 Docker 환경을 띄웁니다:
```bash
# Redis 서버 로컬 구동 (Port 6379)
docker run -d --name local-redis -p 6379:6379 redis:alpine

# PostgreSQL 데이터베이스 로컬 구동 (Redshift Data Warehouse 모사용, Port 5432)
docker run -d --name local-dw \
  -e POSTGRES_DB=cosmetics_dw \
  -e POSTGRES_USER=awsuser \
  -e POSTGRES_PASSWORD=SecurePass123 \
  -p 5432:5432 postgres:14-alpine
```

### 3-2. AWS 실환경 (ElastiCache & Redshift)
* **Amazon ElastiCache for Redis**:
  * 엔진 버전: `Redis 7.x 이상`
  * 유형: 캐시 히트율 보장을 위한 고가용성 Multi-AZ (클러스터 모드 활성화 권장)
  * 포트: 기본 포트 `6379`를 사용하고 보안그룹에서 EKS 노드 그룹 및 ECS의 접근 권한 허용
* **Amazon Redshift**:
  * 노드 타입: 대규모 집계 분석용 `ra3.xlplus` 이상 추천
  * 스키마: `public.user_item_interactions` (로그 집계 결과 저장)

---

## 4. Apache Spark / Glue ETL 로컬 테스트 환경

Glue PySpark 스크립트(`scripts/glue_etl.py`)를 클라우드 배포 전에 로컬에서 검증하는 환경입니다.

### 4-1. 필수 소프트웨어 요구사항
- **Java Development Kit (JDK)**: OpenJDK 11 혹은 8
- **Apache Spark**: Spark 3.2.x 또는 Glue 버전 호환 빌드
- **Python**: Python 3.8 ~ 3.10

### 4-2. 로컬 PySpark 구동 테스트
Spark 라이브러리가 로컬 환경에 설치된 상태에서 로컬 세션을 열어 ETL 흐름을 돌려볼 수 있습니다.
```bash
# 로컬 Spark 라이브러리 및 Pandas 패키지 설치
pip install pyspark==3.2.1 pandas

# 로컬 파일 기준 스크립트 실행 테스트
python3 scripts/glue_etl.py \
  --JOB_NAME "local_test_job" \
  --S3_INPUT_PATH "file:///Users/beom/workspace/projects/sesac/original_assets/" \
  --REDSHIFT_TEMP_DIR "file:///tmp/spark-temp" \
  --REDSHIFT_CONNECTION "jdbc:postgresql://localhost:5432/cosmetics_dw"
```
*(참고: 로컬 테스트 시에는 Redshift Connection 매개변수에 PostgreSQL JDBC URL을 넘겨 모의 적재합니다.)*
