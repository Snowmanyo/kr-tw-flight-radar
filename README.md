# 韓台機票雷達

比較台北(TPE/TSA)⇄韓國(ICN/GMP/PUS/CJJ)多機場機票的監控小工具。

- `index.html` — 看板(GitHub Pages 線上看板的頁面),可切換來回/單程,依航空與時段篩選。
- `data.json` — 最新一次抓到的票價(由排程自動更新)。
- `flights.py` — 抓價引擎(抓 Google Flights,解析票價)。
- `config.json` — 你的設定:機場、候選日、乘客、篩選等。
- `run_cycle.sh` + `com.flightradar.scrape.plist` — 本機每 3 小時自動抓價並推上 GitHub。

資料為 Google Flights 參考價,訂票前請至航空公司官網確認。
