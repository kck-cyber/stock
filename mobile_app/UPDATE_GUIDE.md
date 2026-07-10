# Android 업데이트 설치 안내

## 업데이트 설치 조건

Android에서 기존 앱을 지우지 않고 업데이트하려면 아래 조건을 지켜야 합니다.

- `bundle_id`는 계속 `com.kck.morningstock`이어야 합니다.
- APK를 만들 때마다 `build_number`가 이전 APK보다 커야 합니다.
- 같은 서명 키로 빌드해야 합니다.

위 조건이 맞으면 휴대폰에서 새 APK를 열었을 때 `업데이트`로 설치됩니다.

## 평소 빌드

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -RunBuild
```

## 업데이트용 APK 빌드

업데이트용 APK를 만들 때는 빌드 번호를 자동으로 올립니다.

```powershell
powershell -ExecutionPolicy Bypass -File mobile_app\build_apk.ps1 -BumpBuildNumber -RunBuild
```

빌드가 성공하면 `dist_mobile` 폴더에 APK가 생성됩니다.

## 휴대폰에 옮겨 설치

1. 생성된 APK를 휴대폰으로 옮깁니다.
2. 휴대폰에서 APK를 엽니다.
3. 기존 앱이 설치되어 있으면 `업데이트`로 표시됩니다.
4. 설치 후 기존 앱 내부 저장 데이터는 유지됩니다.

## 주의

- 앱을 삭제한 뒤 설치하면 앱 내부 저장 데이터도 지워질 수 있습니다.
- `bundle_id`를 바꾸면 Android는 완전히 다른 앱으로 인식합니다.
- 다른 PC나 다른 서명 키로 빌드하면 업데이트 설치가 거부될 수 있습니다.
- 안정적인 배포를 하려면 나중에 전용 Android 서명 키를 만들어 계속 같은 키로 빌드하는 방식이 좋습니다.
