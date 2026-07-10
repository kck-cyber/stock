# APK 빌드 준비 체크리스트

## 1. 빌드 전 확인

- `python mobile_app/main.py`로 PC에서 앱 실행 확인
- `설정` 탭에서 저장 데이터 연결 상태 확인
- 앱 시작 후 자동 실제 데이터 새로고침 상태 확인
- `실제 분석 데이터 불러오기` 버튼 수동 동작 확인
- `자동 새로고침` 스위치 동작 확인
- 하단 탭 `홈`, `관심`, `브리핑`, `차트`, `설정` 화면 확인
- `브리핑` 안의 `요약`, `뉴스`, `재무` 전환 확인
- `mobile_app/assets/icon.png`와 `mobile_app/assets/splash.png` 확인

## 2. 모바일 빌드 주의점

현재 모바일 앱은 PC 프로젝트의 `storage`와 `src`를 읽을 수 있는 개발 환경 기준으로 만들어져 있습니다. APK로 빌드하면 PC 폴더를 그대로 읽을 수 없기 때문에 다음 중 하나가 필요합니다.

- 앱 내부 저장소에 관심종목/보유종목을 따로 저장: 구현 완료
- PC 프로그램에서 백업 파일을 내보내고 앱에서 가져오기
- PC 분석 엔진을 로컬 API 또는 서버 API로 분리

즉, APK 첫 버전은 UI와 앱 내부 저장 기능 중심으로 만들고, 무거운 분석은 API로 분리하는 방식이 가장 안정적입니다.

## 3. 빌드 명령 확인

드라이런:

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1
```

실제 APK 빌드:

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -RunBuild
```

업데이트용 APK 빌드:

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -BumpBuildNumber -RunBuild
```

업데이트 설치 조건은 `mobile_app/UPDATE_GUIDE.md`를 확인하세요.

## 4. 빌드 산출물

빌드가 성공하면 기본 산출물은 프로젝트 루트의 `dist_mobile` 폴더에 생성됩니다.

## 5. 다음 정리 작업

- PC 분석 엔진 API 분리
- Android 빌드에서 아이콘 파일이 실제로 반영되는지 확인
- 실제 휴대폰 화면에서 최종 레이아웃 점검
