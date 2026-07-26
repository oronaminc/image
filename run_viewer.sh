#!/bin/bash
# =====================================================================
#  이미지 뷰어 항상 켜두기 (죽으면 자동 재시작 + 코드 고치면 자동 반영)
#  시작:  nohup bash run_viewer.sh >/dev/null 2>&1 &
#  종료:  pkill -f run_viewer.sh ; pkill -f "imagecollector serve"
#  주소:  http://127.0.0.1:8765  (항상 이 주소로 열려 있어야 한다)
# =====================================================================
cd "$(dirname "$0")" || exit 1
PORT="${1:-8765}"

# 이미 떠 있으면 중복 실행 방지 (포트를 뺏으려 하지 않는다)
if curl -s -o /dev/null "http://127.0.0.1:${PORT}/" 2>/dev/null; then
  echo "[keep-alive] $(date '+%F %T') 이미 ${PORT} 에서 실행 중 → 종료" >> .viewer.log
  exit 0
fi

while true; do
  echo "[keep-alive] $(date '+%F %T') 뷰어 시작 (port ${PORT}, 자동 리로드)" >> .viewer.log
  # --reload: 소스를 고쳐도 뷰어를 죽였다 살릴 필요가 없다(작업 중 접속 유지)
  .venv/bin/python -m imagecollector serve --host 127.0.0.1 --port "${PORT}" --reload >> .viewer.log 2>&1
  echo "[keep-alive] $(date '+%F %T') 뷰어 종료됨 → 3초 후 재시작" >> .viewer.log
  sleep 3
done
