# Mobile Assets

이 폴더는 모바일 앱 빌드에 사용할 아이콘과 스플래시 이미지를 보관합니다.

## 파일

- `icon.png`: 기본 앱 아이콘, 1024x1024
- `adaptive_icon_foreground.png`: Android adaptive icon foreground 후보, 1024x1024
- `splash.png`: 모바일 스플래시 이미지, 1242x2688

## 재생성

아래 명령으로 이미지를 다시 만들 수 있습니다.

```powershell
python mobile_app\tools\generate_assets.py
```

색상과 글자, 차트 모양은 `mobile_app/tools/generate_assets.py`에서 수정합니다.
