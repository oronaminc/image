# 웹 뷰어 항상 켜두기 (Always-on)

새 이미지가 들어오면 갤러리 하단에 **🆕 라이브 배너**가 뜹니다(6초 폴링). 서버만 계속 켜두면 됩니다.

## 방법 1) keep-alive 스크립트 (권장 · 즉시 사용)

프로젝트 루트에서:

```bash
# 시작 (죽으면 자동 재시작, 터미널 닫아도 유지)
nohup bash run_viewer.sh 8765 >/dev/null 2>&1 &

# 상태 확인
curl -s http://127.0.0.1:8765/api/count

# 종료
pkill -f run_viewer.sh ; pkill -f "imagecollector serve"
```

- 서버가 죽으면 3초 내 자동 재시작합니다.
- Mac 이 켜져 있는 동안 계속 유지됩니다. (재부팅 후에는 위 명령을 다시 실행)

## 방법 2) launchd 서비스 (재부팅 후에도 자동 시작)

`com.oronaminc.imagecollector.viewer.plist` 를 `~/Library/LaunchAgents/` 에 두고 등록하면
**로그인 시 자동 시작 + 죽으면 자동 재시작**됩니다.

⚠️ **주의**: 이 프로젝트가 `~/Desktop` 아래에 있으면 macOS 개인정보 보호(TCC) 때문에
launchd 프로세스가 접근을 거부당합니다(`Operation not permitted`). 두 가지 해결책:

1. **전체 디스크 접근 권한 부여** (한 번만):
   시스템 설정 → 개인정보 보호 및 보안 → **전체 디스크 접근** 에
   `/Users/1113177/Desktop/github/image/.venv/bin/python` 를 추가.
2. 또는 프로젝트를 `~/Desktop` 밖(예: `~/imagecollector`)으로 옮기기.

등록/해제:

```bash
cp deploy/com.oronaminc.imagecollector.viewer.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.oronaminc.imagecollector.viewer.plist

# 해제
launchctl bootout gui/$(id -u)/com.oronaminc.imagecollector.viewer
```

권한 문제 없이 바로 되는 **방법 1** 을 추천합니다.
