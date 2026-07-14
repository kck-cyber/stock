# Windows 배포 가이드

## 실행 파일 위치

PC 실행 파일은 아래 위치에 생성됩니다.

```text
dist\MorningStockAssistantPro\MorningStockAssistantPro.exe
```

`MorningStockAssistantPro.exe`는 `_internal` 폴더와 같은 위치에 있어야 합니다. exe 파일만 따로 옮기면 실행되지 않습니다.

## 배포 zip 만들기

이미 빌드된 exe를 zip으로 묶을 때:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_release.ps1 -SkipBuild
```

코드 검사, exe 빌드, zip 생성을 한 번에 할 때:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_release.ps1
```

완성된 zip은 `releases` 폴더에 생성됩니다.

## 업데이트할 때 데이터 보존

관심종목, 보유정보, 알림 설정은 실행 폴더의 `storage` 폴더에 저장됩니다.

배포 zip에는 `storage` 폴더를 포함하지 않습니다. 그래서 기존 폴더에 새 zip을 덮어써도 기존 데이터가 함께 지워질 가능성을 줄였습니다.

그래도 큰 업데이트 전에는 프로그램의 백업 기능으로 먼저 백업하는 것을 권장합니다.
