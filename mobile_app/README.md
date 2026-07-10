# Morning Stock Mobile App

Flet 기반 모바일 앱 초안입니다. PC 버전에서 쓰는 `storage` 데이터를 읽고, 모바일 화면에서 관심종목과 보유 정보를 확인/수정할 수 있도록 구성했습니다.

## 실행

프로젝트 루트에서:

```powershell
python mobile_app/main.py
```

또는:

```powershell
flet run mobile_app/main.py
```

## 현재 기능

- `storage/watchlist.json` 관심종목 읽기
- `storage/holdings.json` 보유종목 읽기/저장/삭제
- 홈 대시보드
- 관심종목 추가/삭제
- 보유 수량과 평균가 입력
- AI 퀀트 브리핑 요약 화면
- 브리핑 내부 `요약/뉴스/재무` 전환 화면
- 모바일용 토스 스타일 차트 UI
- 데이터 파일 연결 상태 표시
- PC 분석 엔진 브릿지 연결
- 설정 화면에서 새로고침 실행
- 실제 분석 로딩 표시
- 실제 분석 중 중복 실행 방지
- 앱 시작 후 자동 새로고침
- 30분 주기 자동 새로고침
- 홈 화면 실시간 데이터 새로고침 패널
- 애널리스트 목표가/상승여력 표시
- 차트 상세 지표와 선택 지점 가격 표시
- 차트 20일선/40일선/60일선 표시
- 여러 종목 병렬 분석으로 새로고침 속도 개선
- Render 분석 서버 URL 설정
- 서버 분석 실패 시 로컬 분석 자동 전환

## 아직 남은 작업

1. 분석 취소 버튼 추가
2. Android 빌드에서 아이콘 반영 확인
3. 실제 Render 배포 후 휴대폰 네트워크 테스트
4. 실제 휴대폰에서 최종 레이아웃 점검

## APK 빌드 준비

빌드 설정은 아래 파일에 정리했습니다.

- `mobile_app/app_config.json`
- `mobile_app/pyproject.toml`
- `mobile_app/build_apk.ps1`
- `mobile_app/BUILD_CHECKLIST.md`
- `mobile_app/assets/icon.png`
- `mobile_app/assets/splash.png`

빌드 명령 확인:

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1
```

실제 APK 빌드:

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -RunBuild
```

## 실제 분석 데이터 사용

앱의 홈 또는 설정 탭에서 `새로고침`을 누르면 PC 버전의 `StockService`와 `StockAnalyzer`를 호출합니다. 성공하면 관심종목 카드, 브리핑 점수, 뉴스, 재무, 애널리스트 의견, 차트 데이터가 실제 수집 데이터 우선으로 표시됩니다.

Render 서버를 배포한 뒤 설정 탭의 `분석 서버`에 Render URL을 저장하면 앱은 서버 분석을 먼저 사용합니다. 서버 요청이 실패하면 기존 로컬 분석으로 자동 전환합니다.

## 저장 위치

PC 개발 실행에서는 프로젝트 루트의 `storage` 폴더를 그대로 사용합니다. APK처럼 프로젝트 폴더가 없는 환경에서는 Flet 앱 내부 저장소 아래 `storage` 폴더를 사용합니다.

앱 내부 저장소가 비어 있고 PC 개발 저장소가 있으면 최초 실행 시 `watchlist.json`, `holdings.json`을 한 번 복사합니다.

## 자동 새로고침

앱이 실행되면 관심종목이 있는 경우 실제 데이터를 자동으로 한 번 불러옵니다. 이후 기본값으로 30분마다 자동 새로고침을 실행합니다.

설정 탭의 `자동 새로고침` 스위치로 켜고 끌 수 있습니다.

## 참고

Android APK로 빌드할 때는 `pandas`, `numpy`, `yfinance`, `pykrx` 같은 패키지가 모바일 환경에서 바로 동작하지 않을 수 있습니다. 그래서 모바일 앱은 UI와 저장 데이터 중심으로 만들고, 무거운 분석은 PC 앱 또는 별도 API에서 처리하는 방식을 권장합니다.
