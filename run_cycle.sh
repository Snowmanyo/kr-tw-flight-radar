#!/bin/bash
# 每次排程執行:先本機抓價(已驗證可行),再把最新 data.json 推上 GitHub,
# GitHub Pages 看板就會自動更新,手機隨處可看。推送失敗不影響本機抓價與歷史。
set -u
DIR="/Users/c/Desktop/claude code/機票小工具"
cd "$DIR" || exit 1

LOG="$DIR/cron.log"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始 =====" >> "$LOG"

# 1) 抓價(本機 IP,已驗證)
"$DIR/.venv/bin/python" "$DIR/flights.py" >> "$LOG" 2>&1
echo "抓價完成" >> "$LOG"

# 2) 推上 GitHub(更新線上看板)
if git -C "$DIR" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$DIR" add data.json history.json >> "$LOG" 2>&1
  if ! git -C "$DIR" diff --cached --quiet; then
    git -C "$DIR" commit -m "更新票價 $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
    git -C "$DIR" push >> "$LOG" 2>&1 \
      && echo "已推上 GitHub,線上看板更新中" >> "$LOG" \
      || echo "git push 失敗(不影響本機資料)" >> "$LOG"
  else
    echo "價格無變動,不推送" >> "$LOG"
  fi
fi

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 結束 =====" >> "$LOG"
