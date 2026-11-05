#!/bin/bash
# 雙擊這個檔 = 現在抓一次最新機票價、更新看板。看完關掉視窗即可。
cd "/Users/c/kr-tw-flight-radar" || { echo "找不到專案資料夾"; read -n1; exit 1; }
clear
echo "===== 韓台機票雷達:現在抓價 ====="
echo "抓取中,請稍候(視日期範圍約數分鐘)…"
echo ""
.venv/bin/python flights.py
echo ""

# 推上 GitHub(讓手機也能看到這次結果)
git add data.json history.json >/dev/null 2>&1
if git commit -m "手動抓價 $(date '+%m-%d %H:%M')" >/dev/null 2>&1; then
  git push >/dev/null 2>&1 && echo "✓ 已更新線上看板(手機可看):https://snowmanyo.github.io/kr-tw-flight-radar/"
else
  echo "(價格無變動)"
fi
echo ""

# 本機立即開看板看最新結果
PORT=8799
python3 -m http.server $PORT >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
sleep 1
open "http://localhost:$PORT/index.html"
echo "看板已在瀏覽器開啟 ✈"
echo "看完後,關掉這個視窗即可結束。"
echo ""
echo "(按 Ctrl-C 或關視窗結束)"
wait $SRV
