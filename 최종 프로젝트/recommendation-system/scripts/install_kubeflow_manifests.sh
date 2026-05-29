#!/bin/bash
# ==============================================================================
# 새싹 방범대 - EKS Kubeflow 플랫폼 설치 및 Manifests 배포 자동화 스크립트
# ==============================================================================
set -e

echo "=========================================================="
echo "Kubeflow v1.8.0 플랫폼 설치 자동화 스크립트 실행"
echo "=========================================================="

# 1. Kustomize v5.0.3 버전 체크 및 설치
KUSTOMIZE_VERSION="v5.0.3"
if command -v kustomize &> /dev/null; then
    CURRENT_VERSION=$(kustomize version | awk '{print $1}' | cut -d/ -f2)
    echo "감지된 Kustomize 버전: $CURRENT_VERSION"
else
    CURRENT_VERSION=""
fi

if [ "$CURRENT_VERSION" != "$KUSTOMIZE_VERSION" ]; then
    echo "Kustomize $KUSTOMIZE_VERSION 설치를 진행합니다..."
    OS_TYPE="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH_TYPE="$(uname -m)"
    if [ "$ARCH_TYPE" = "x86_64" ]; then
        ARCH_TYPE="amd64"
    elif [ "$ARCH_TYPE" = "arm64" ] || [ "$ARCH_TYPE" = "aarch64" ]; then
        ARCH_TYPE="arm64"
    fi
    
    KUSTOMIZE_URL="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_${OS_TYPE}_${ARCH_TYPE}.tar.gz"
    echo "다운로드 URL: $KUSTOMIZE_URL"
    curl -LO "$KUSTOMIZE_URL"
    tar -zxvf kustomize_${KUSTOMIZE_VERSION}_*.tar.gz
    sudo mv kustomize /usr/local/bin/
    rm -f kustomize_${KUSTOMIZE_VERSION}_*.tar.gz
    echo "Kustomize 설치 완료: $(kustomize version)"
fi

# 2. Kubeflow Manifests 레포지토리 복제
MANIFESTS_DIR="/tmp/kubeflow-manifests"
if [ ! -d "$MANIFESTS_DIR" ]; then
    echo "Kubeflow Manifests v1.8.0 소스 복제 중..."
    git clone https://github.com/kubeflow/manifests.git "$MANIFESTS_DIR" -b v1.8.0
fi
cd "$MANIFESTS_DIR"

# 3. K8s 클러스터 연결 확인
echo "Kubernetes 클러스터 연결 상태 확인 중..."
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Kubernetes 클러스터에 연결할 수 없습니다. kubeconfig 설정을 확인해주세요."
    exit 1
fi

# 4. 순차 빌드 및 배포 (CRD 의존성 해결용 루프 포함)
echo "1단계: Cert-Manager 및 기본 인프라(Istio) 배포..."
while ! kustomize build common/cert-manager/cert-manager/base | kubectl apply -f -; do
    echo "Cert-Manager 설치 재시도 중 (10초 대기)..."
    sleep 10
done

while ! kustomize build common/istio-ca/base | kubectl apply -f -; do
    echo "Istio-CA 설치 재시도 중 (5초 대기)..."
    sleep 5
done

while ! kustomize build common/istio/istio-install/base | kubectl apply -f -; do
    echo "Istio 설치 재시도 중 (5초 대기)..."
    sleep 5
done

echo "2단계: Dex OIDC & OAuth2 프록시 인증 엔진 설치..."
kustomize build common/dex/overlays/oauth2-proxy | kubectl apply -f -

echo "3단계: Kubeflow 핵심 파이프라인(KFP) 및 포털 대시보드 설치..."
while ! kustomize build apps/pipeline/upstream/env/cert-manager/platform-agnostic-multi-user | kubectl apply -f -; do
    echo "Kubeflow Pipelines 설치 재시도 중 (10초 대기)..."
    sleep 10
done

kustomize build apps/profiles/upstream/overlays/kubeflow | kubectl apply -f -
kustomize build apps/centraldashboard/upstream/overlays/istio | kubectl apply -f -

echo "=========================================================="
echo "Kubeflow Manifests가 성공적으로 클러스터에 배포되었습니다!"
echo "외부 Ingress Gateway 주소를 확인하려면 아래 명령어를 사용하세요:"
echo "kubectl get svc istio-ingressgateway -n istio-system"
echo "=========================================================="
