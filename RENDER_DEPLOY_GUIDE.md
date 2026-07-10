# Render 서버 배포 가이드

모바일 앱이 직접 `pandas`, `yfinance`, `pykrx` 기반 분석을 돌리면 느릴 수 있습니다. Render 서버는 무거운 분석을 서버에서 처리하고 앱은 결과 JSON만 받도록 분리합니다.

## 배포 파일

- `server/main.py`: FastAPI 서버
- `render.yaml`: Render 배포 설정
- `requirements-render.txt`: 서버 전용 의존성

## Render 배포

1. Render에서 새 Web Service를 만듭니다.
2. 이 저장소를 연결합니다.
3. Render가 `render.yaml`을 인식하면 아래 설정으로 실행합니다.

```text
Build Command: pip install -r requirements-render.txt
Start Command: uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

## 앱에서 서버 사용

Render 배포가 끝나면 `https://서비스이름.onrender.com` 형태의 URL이 생깁니다.

모바일 앱에서:

1. `설정` 탭으로 이동합니다.
2. `분석 서버`의 `Render 서버 URL`에 Render URL을 입력합니다.
3. `서버 설정 저장`을 누릅니다.
4. 새로고침하면 서버 분석을 먼저 사용합니다.

서버 요청이 실패하면 앱은 기존 로컬 분석으로 자동 전환합니다.

## PC 프로그램에서 서버 사용

PC 프로그램에서도 같은 Render URL을 사용할 수 있습니다.

1. PC 프로그램을 실행합니다.
2. `알림` 탭으로 이동합니다.
3. `Render 서버 URL`에 Render URL을 입력합니다.
4. `설정 저장`을 누릅니다.

이후 단일 분석, 비교표, 포트폴리오, 브리핑 누락 분석은 서버를 먼저 사용합니다. 서버 요청이 실패하면 기존 로컬 분석으로 자동 전환합니다.

## 확인용 URL

```text
https://서비스이름.onrender.com/health
```

`{"status":"ok"}`가 나오면 서버가 켜진 상태입니다.

## 참고

Render 무료 플랜은 한동안 요청이 없으면 서버가 잠들 수 있습니다. 첫 요청은 느릴 수 있지만, 이후 새로고침은 휴대폰에서 직접 분석하는 것보다 가벼워집니다.
