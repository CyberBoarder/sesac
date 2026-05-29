# 데브옵스 트러블슈팅 가이드 (DevOps Troubleshooting Guide)

본 문서는 **새싹 방범대** 인프라 및 머신러닝 모델 운영 과정에서 발생하는 대표적인 장애 케이스와 해결 방법 및 재발 방지책을 정리한 트러블슈팅 가이드입니다.

---

## 1. Dex OIDC 연동 및 로그인 후 403 Forbidden 에러

### 1-1. 현상
* 사용자가 Dex 로그인 페이지를 통해 외부 IdP(예: Google, LDAP) 또는 정적 계정으로 로그인은 정상 완료했으나, Kubeflow 대시보드(Central Dashboard)로 리다이렉트되는 과정에서 `403 Forbidden` 혹은 `Registration Flow` 루프 에러가 발생합니다.

### 1-2. 원인 분석
1. **OAuth2 Redirect URI 미스매치**:
   - Dex 설정의 `redirectURIs`와 Kubeflow `OIDC-AuthService`에 설정된 클라이언트 Callback URL이 일치하지 않을 때 발생합니다.
2. **Kubernetes Namespace 및 RBAC 권한 부재**:
   - 로그인한 사용자의 이메일 주소(예: `june508v@kbu.ac.kr`)에 매핑되는 Kubernetes Profile 및 Namespace가 자동으로 생성되지 않았거나, 이에 해당하는 RBAC(`RoleBinding` / `ClusterRoleBinding`) 권한이 없어서 Dashboard API 호출이 거부당한 상태입니다.
3. **EKS APIServer OIDC Flags 미지정**:
   - Kube-APIServer의 OIDC Issuer URL 및 Client ID 설정이 누락되어 JWT 토큰의 유효성을 검증하지 못하는 상황입니다.

### 1-3. 문제 진단 & 트러블슈팅 커맨드
1. **Dex 포드 로그 확인**:
   ```bash
   kubectl logs -n auth -l app=dex --tail=100
   ```
   *로그에서 `redirect_uri_mismatch` 혹은 `token exchange failed` 에러 유무 확인.*

2. **OIDC AuthService 설정 확인**:
   ```bash
   kubectl get configmap oidc-authservice-parameters -n kubeflow -o yaml
   ```

3. **로그인 유저 권한 및 네임스페이스 생성 여부 확인**:
   ```bash
   kubectl get profiles
   kubectl get rolebinding -n <user-namespace>
   ```

### 1-4. 해결 방안 (조치 사항)
1. **Dex 설정 업데이트**:
   Dex ConfigMap에서 `redirectURIs`에 올바른 서비스 도메인과 콜백 패스를 적용합니다:
   ```bash
   kubectl edit configmap dex -n auth
   ```
   ```yaml
   # ConfigMap 내 설정 변경 내용 예시
   staticClients:
   - id: kubeflow-oidc-authservice
     redirectURIs:
     - 'https://kubeflow.sesac.beom.site/login'
     name: 'Kubeflow OIDC AuthService'
     secret: <client-secret-key>
   ```
2. **Dex 서비스 재시작**:
   ```bash
   kubectl rollout restart deployment dex -n auth
   kubectl rollout restart statefulset oidc-authservice -n kubeflow
   ```

---

## 2. Kubeflow 파이프라인 Pod의 ImagePullBackOff 장애

### 2-1. 현상
* Kubeflow 파이프라인에서 모델 학습 컴포넌트(`ML Training Stage`) 실행 시 Pod 상태가 `Pending`에 머물며, `kubectl get pods` 확인 시 `ImagePullBackOff` 또는 `ErrImagePull` 에러가 발생합니다.

### 2-2. 원인 분석
1. **AWS ECR 레지스트리 인증 만료 (Credential Expiration)**:
   - ECR 로그인 토큰은 기본적으로 12시간 동안만 유효합니다. EKS 노드가 프라이빗 ECR에서 이미지를 당겨오기 위한 인증 갱신 메커니즘이 원활하지 않을 때 발생합니다.
2. **IAM 역할(IAM Role) 권한 누락**:
   - EKS Worker Node의 EC2 인스턴스 프로파일에 ECR에서 이미지를 읽을 수 있는 `AmazonEC2ContainerRegistryReadOnly` 정책이 부여되지 않았습니다.
3. **프라이빗 서브넷 NAT Gateway 라우팅 에러**:
   - EKS 노드가 프라이빗 서브넷에 있고 인터넷 외부의 ECR 레지스트리로 통신할 수 있는 NAT Gateway 라우팅 테이블 설정에 장애가 있을 경우 이미지를 내려받지 못합니다.

### 2-3. 문제 진단 & 트러블슈팅 커맨드
1. **Pod 이벤트 상세 로그 조회**:
   ```bash
   kubectl describe pod <training-pod-name> -n kubeflow
   ```
   *출력 결과 하단의 `Events` 영역에서 `AccessDeniedException` 또는 `Failed to pull image` 메시지 및 ECR URI를 확인합니다.*

2. **EKS 노드의 IAM 역할 및 권한 조회**:
   ```bash
   aws iam simulate-principal-policy \
     --policy-source-arn arn:aws:iam::123456789012:role/eks-worker-node-role \
     --action-names ecr:GetDownloadUrlForLayer ecr:BatchGetImage
   ```

### 2-4. 해결 방안 (조치 사항)
1. **EKS 노드 인프라 IAM 정책 부여**:
   Terraform 파일 혹은 AWS Console에서 EKS Node IAM Role에 ECR Read 정책을 할당합니다:
   ```bash
   aws iam attach-role-policy \
     --role-name eks-worker-node-role \
     --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
   ```
2. **Kubernetes ImagePullSecret 생성 및 매핑 (필요 시)**:
   AWS CLI를 통해 ECR 패스워드를 받아 온 후 K8s Secret으로 등록합니다:
   ```bash
   # ECR 로그인 패스워드 추출
   ECR_PASSWORD=$(aws ecr get-login-password --region ap-northeast-2)
   
   # Kubernetes Secret 생성
   kubectl create secret docker-registry ecr-registry-secret \
     --docker-server=123456789012.dkr.ecr.ap-northeast-2.amazonaws.com \
     --docker-username=AWS \
     --docker-password=$ECR_PASSWORD \
     -n kubeflow
   ```
   *이후 파이프라인 YAML 명세 내 `imagePullSecrets`에 `ecr-registry-secret`을 정의합니다.*
