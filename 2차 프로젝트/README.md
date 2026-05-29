# 2차 세미 프로젝트 - 쿠버네티스를 활용한 웹로그 수집 인프라 구축

본 프로젝트는 회원제 쇼핑몰의 요구사항을 반영하여 고가용성 클라우드 인프라를 구축하고, 사용자 클릭 로그를 실시간으로 수집 및 분석할 수 있는 데이터 파이프라인을 구현하는 것을 목표로 진행되었습니다.

---

## 1. 프로젝트 개요
* **프로젝트명**: 쿠버네티스를 활용한 웹로그 수집 인프라 구축 (2차 세미 프로젝트)
* **진행 기간**: 2024.12.19 ~ 2024.12.27
* **주요 목표**:
  - 회원제 쇼핑몰 비즈니스 요구사항에 맞춰 프로모션 페이지 등을 신속히 배포할 수 있는 고가용성 클라우드 인프라 설계
  - 사용자별 상품 선호도 파악 및 A/B 테스트 검증용 실시간 클릭 로그 수집 파이프라인 연동
  - 플랫폼의 내부 보안 통제 및 인적 자원 모니터링 환경 확보

---

## 2. 기술 스택 (Tech Stack)
* **Cloud Platform**: GCP (Google Cloud Platform), GKE - Autopilot
* **Development / DB**: Spring Boot, MySQL, Thymeleaf
* **Log Ingestion & Analysis**: GCP Pub/Sub, Cloud Dataflow, Elastic Cloud (Elasticsearch, Kibana)
* **CI/CD**: Jenkins, Docker, Docker Hub, GitHub
* **Monitoring**: Cloud Operations, Managed Service for Prometheus

---

## 3. 개인 담당 역할 및 수행 내용 (솔루션 아키텍트)
본 프로젝트에서 솔루션 아키텍트(Solutions Architect) 역할을 전담하여 전체 클라우드 인프라 아키텍처 설계, 구축 및 운영 모니터링 체계를 수립했습니다.

* **인프라 구성 및 GKE Autopilot 구축**:
  - GKE Autopilot 클러스터를 사용하여 노드 레벨 관리 부담을 최소화하고 리소스 자동 확장이 용이한 탄력적 운영 환경을 마련했습니다.
* **도메인 및 라우팅 연동**:
  - Cloud DNS와 Cloud Load Balancing을 구성하여 외부 사용자 접근 경로(`syb0612.shop`)를 정의하고 HTTPS/HTTP 로드밸런싱 구조를 구현했습니다.
* **데이터베이스 보안 튜닝**:
  - MySQL DB 서버에 악성 익명 라우팅 네트워크(Tor exit nodes)로부터 오는 인그레스 트래픽을 거부(Deny)하는 방화벽 규칙을 적용해 인프라 취약성을 보강했습니다.
* **통합 인프라 모니터링**:
  - Cloud Operations와 Managed Service for Prometheus를 통합하여 전체 배포 Pod 수(43개) 및 컨테이너(84개) 정보, CPU/Memory 리소스 사용 지표를 한눈에 관측할 수 있는 대시보드를 시각화했습니다.

---

## 4. 데이터 수집 파이프라인 흐름
사용자 행동 로그가 끊김 없이 수집 및 분석되는 실시간 데이터 흐름입니다.
```
[사용자 클릭] 
   │ (JSON 포맷 전송)
   ▼
[GCP Pub/Sub]   <--- 순서 키(ordering key) 및 지수 백오프 재시도 규칙 반영
   │
   ▼
[GCP Dataflow]  <--- 실시간 스트리밍 처리 및 파싱
   │
   ▼
[Elastic Cloud] <--- Elasticsearch 인덱싱 및 Kibana 대시보드를 통한 시각화
```

---

## 5. 핵심 트러블슈팅 경험

### 5-1. GKE Autopilot 보안 제약에 따른 모니터링/로그 아키텍처 전환
* **문제 상황**: GKE Autopilot의 엄격한 보안 제약 정책으로 인해 시스템 네임스페이스(`kube-system`)에 높은 권한을 요구하는 Helm 기반 EFK(Fluentd 등), Prometheus 및 Grafana 직접 배포가 차단되는 에러가 발생했습니다.
* **해결 방안**: 클러스터 내부에 Elasticsearch를 배포하는 대신 호스팅형 **Elastic Cloud(SaaS)** 환경을 연계하고, 모니터링은 구글의 매니지드 서비스인 **Managed Service for Prometheus** 및 **Cloud Operations** 내장 대시보드를 사용하도록 아키텍처를 전면 개편했습니다.
* **결과**: 클러스터 보안 가이드라인을 침해하지 않으면서도 안정적인 관측 성능을 유지하고 리소스 운영 효율을 개선했습니다.

### 5-2. CI/CD 자격증명 노출 방지
* **문제 상황**: GCP 서비스 계정 키 파일 등 민감 자격증명이 소스코드 저장소에 직접 포함되면서 GitHub Push Protection에 의해 푸시가 거부되고 빌드가 차단되는 문제가 발생했습니다.
* **해결 방안**: 자격증명 파일을 Git에서 완전히 제외하고, **Jenkins Credentials** 플러그인을 도입해 빌드 실행 시점에 보안 바인딩 방식으로 변수를 주입하도록 CI/CD 흐름을 전환했습니다.

### 5-3. Jenkins 권한 불일치 수정
* **문제 상황**: Jenkins 빌드 스키마 동작 중 `Deployment.yaml` 파일의 이미지 태그 수정 후 Git add 처리 시 `detected dubious ownership` 소유권 충돌 에러가 발생했습니다.
* **해결 방안**: `sudo chown -R jenkins:jenkins` 권한 수정 명령을 런북에 통합하여 Jenkins 빌드 에이전트 계정이 소스 디렉터리 권한을 정상 수임하도록 조치했습니다.
