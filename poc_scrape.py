"""概念驗證:用 fast-flights 抓 Google Flights 來回票價。
目的只有一個——確認「抓不抓得到價」。成功就印出班次與價格。
"""
import sys
from fast_flights import FlightQuery, Passengers, create_query, get_flights

# 測試路線:台北(桃園)→ 首爾(仁川)來回
OUT_DATE = "2026-12-20"
RET_DATE = "2026-12-27"

query = create_query(
    flights=[
        FlightQuery(date=OUT_DATE, from_airport="TPE", to_airport="ICN"),
        FlightQuery(date=RET_DATE, from_airport="ICN", to_airport="TPE"),
    ],
    trip="round-trip",
    seat="economy",
    passengers=Passengers(adults=1),
    currency="TWD",
    language="zh-TW",
)

print(f"查詢:TPE⇄ICN  去 {OUT_DATE} / 回 {RET_DATE}  1 成人 經濟艙 TWD")
print("抓取中…")
try:
    result = get_flights(query)
except Exception as e:
    print(f"\n❌ 抓取失敗:{type(e).__name__}: {e}")
    sys.exit(1)

flights = getattr(result, "flights", None) or []
print(f"\n✅ 成功,共 {len(flights)} 筆班次。目前價位標示:{getattr(result,'current_price',None)}\n")
for i, f in enumerate(flights[:8], 1):
    print(f"{i:>2}. {getattr(f,'name','?'):<22} "
          f"去 {getattr(f,'departure','?')} → 到 {getattr(f,'arrival','?')}  "
          f"停點 {getattr(f,'stops','?')}  時長 {getattr(f,'duration','?')}  "
          f"價格 {getattr(f,'price','?')}  {'[最佳]' if getattr(f,'is_best',False) else ''}")
