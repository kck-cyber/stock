# Google Cloud Run 배포 가이드

Render 무료 서버가 잠자기 때문에 첫 접속이 느릴 때, 같은 FastAPI 서버를 Google Cloud Run으로 옮길 수 있습니다.

## 준비

1. Google Cloud 계정과 프로젝트를 준비합니다.
2. Cloud Run, Cloud Build, Artifact Registry API를 활성화합니다.
3. 로컬에 Google Cloud CLI를 설치하고 로그인합니다.

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region asia-northeast3
```

## 최초 1회 저장소 생성

```powershell
gcloud artifacts repositories create morning-stock --repository-format=docker --location=asia-northeast3 --description="Morning Stock API images"
```

## 배포

프로젝트 루트에서 실행합니다.

```powershell
gcloud builds submit --config cloudbuild.yaml
```

배포가 끝나면 Cloud Run 서비스 URL이 출력됩니다. 예:

```text
https://morning-stock-api-xxxxx-du.a.run.app
```

## 앱/PC에 주소 넣기

- 모바일 앱: 설정 탭 -> 분석 서버 URL에 Cloud Run URL 저장
- PC 프로그램: 알림/설정 영역 -> 분석 서버 URL에 Cloud Run URL 저장

정상 확인:

```powershell
curl https://YOUR_CLOUD_RUN_URL/health
```

응답이 아래처럼 나오면 서버는 정상입니다.

```json
{"status":"ok"}
```

## 더 빠르게 하고 싶을 때

Cloud Run도 `min-instances=0`이면 아주 가끔 첫 요청이 느릴 수 있습니다. 항상 빠르게 유지하려면 `cloudbuild.yaml`의 `--min-instances` 값을 `1`로 바꾸면 됩니다. 대신 무료 한도를 더 빨리 사용할 수 있습니다.
