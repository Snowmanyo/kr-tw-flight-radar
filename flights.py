"""機票抓價引擎:對 Google Flights 抓指定路線/日期的票價,解析成結構化資料。

繞過 fast-flights 已過期的內建解析器,直接取原始 HTML,從 aria-label 自行解析。
"""
from __future__ import annotations
import json, re, time, random, itertools, datetime as dt
from pathlib import Path

from fast_flights import FlightQuery, Passengers, create_query, fetch_flights_html

ROOT = Path(__file__).parent
HISTORY = ROOT / "history.json"
SNAPSHOT = ROOT / "data.json"

# aria-label 範例:
# "來回總價 10029 新台幣起。 搭乘台灣虎航的直達航班。 星期日, 12月 20 晚上8:00 於臺灣桃園國際機場出發,
#  星期日, 12月 20 晚上11:30 抵達仁川國際機場。 總交通時間:2 小時 30 分鐘   選擇航班"
_PRICE = re.compile(r"([\d,]+)\s*新台幣")
_AIRLINE = re.compile(r"搭乘(.+?)的")
_STOPS = re.compile(r"的(?:(\d+)\s*(?:次)?轉機|直達)")
_DEP = re.compile(r"(上午|早上|中午|下午|晚上)?\s*(\d{1,2}):(\d{2})\s*於(.+?)出發")
_ARR = re.compile(r"抵達(.+?)(?:。|$)")
_DUR = re.compile(r"總交通時間[：:]\s*(?:(\d+)\s*小時)?\s*(?:(\d+)\s*分)?")


def _to_24h(period: str | None, h: int, m: int) -> int | None:
    """中文 12 小時制 -> 24 小時制的『分鐘數』,方便時段比較。"""
    if period in ("下午", "晚上") and h != 12:
        h += 12
    elif period in ("上午", "早上") and h == 12:
        h = 0
    elif period == "中午":
        h = 12
    return h * 60 + m


def parse_cards(html: str) -> list[dict]:
    """從 Google Flights HTML 解析所有班次卡片。"""
    out = []
    for lab in re.findall(r'aria-label="([^"]*)"', html):
        if "搭乘" not in lab:  # 只留班次卡片,跳過純價格標籤
            continue
        mp = _PRICE.search(lab)
        # Google 偶爾「無法取得總價」(抓不到價),仍保留此班次,price=None,看板標註「官網查」
        price = int(mp.group(1).replace(",", "")) if mp else None
        air = _AIRLINE.search(lab)
        ms = _STOPS.search(lab)
        stops = 0 if (ms and ms.group(1) is None) else (int(ms.group(1)) if ms else None)
        dep = _DEP.search(lab)
        dep_min = _to_24h(dep.group(1), int(dep.group(2)), int(dep.group(3))) if dep else None
        dep_airport = dep.group(4).strip() if dep else None
        arr = _ARR.search(lab.split("出發", 1)[-1]) if dep else None
        du = _DUR.search(lab)
        dur_min = (int(du.group(1) or 0) * 60 + int(du.group(2) or 0)) if du else None
        out.append({
            "price": price,
            "airline": air.group(1).strip() if air else "?",
            "stops": stops,
            "dep_min": dep_min,
            "dep_airport": dep_airport,
            "arr_airport": arr.group(1).strip() if arr else None,
            "duration_min": dur_min,
        })
    # 同價同航空去重
    seen, uniq = set(), []
    for c in out:
        key = (c["price"], c["airline"], c["dep_min"], c["stops"])
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def _query(from_ap, to_ap, out_date, ret_date, trip, cfg) -> list[dict]:
    legs = [FlightQuery(date=out_date, from_airport=from_ap, to_airport=to_ap)]
    if trip == "round-trip":
        legs.append(FlightQuery(date=ret_date, from_airport=to_ap, to_airport=from_ap))
    q = create_query(
        flights=legs, trip=trip, seat=cfg.get("艙等", "economy"),
        passengers=Passengers(adults=cfg["乘客"].get("大人", 1),
                              children=cfg["乘客"].get("兒童", 0)),
        currency=cfg.get("幣別", "TWD"), language="zh-TW",
    )
    return parse_cards(fetch_flights_html(q))


def _candidate_dates(cfg):
    """合併「候選日」明確清單 + 「日期範圍」自動展開(出發日範圍 × 停留天數)。"""
    out = list(cfg.get("候選日", []))
    dr = cfg.get("日期範圍", {})
    if dr.get("啟用"):
        d0 = dt.date.fromisoformat(dr["出發日起"])
        d1 = dt.date.fromisoformat(dr["出發日迄"])
        stays = dr.get("停留天數", [7]) or [7]
        day = d0
        while day <= d1:
            for s in stays:
                out.append({"去程": day.isoformat(),
                            "回程": (day + dt.timedelta(days=s)).isoformat()})
            day += dt.timedelta(days=1)
    seen, uniq = set(), []
    for e in out:
        k = (e["去程"], e.get("回程"))
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return uniq


def _combos(cfg, trip):
    """產生要查的 (from, to, 去, 回, 方向標籤) 組合。"""
    tw, kr = cfg["台北機場"], cfg["韓國機場"]
    openjaw = cfg.get("開放不同進出點_openjaw", False)
    for d in _candidate_dates(cfg):
        out_date, ret_date = d["去程"], d.get("回程")
        if trip == "round-trip":
            if openjaw:
                for a, b in itertools.product(tw, kr):
                    yield (a, b, out_date, ret_date, f"{a}⇄{b}")
            else:
                for a, b in itertools.product(tw, kr):
                    yield (a, b, out_date, ret_date, f"{a}⇄{b}")
        else:  # one-way:對每個候選日,兩個方向都抓(台北→韓國、韓國→台北),不配對
            for a, b in itertools.product(tw, kr):
                yield (a, b, out_date, None, f"{a}→{b}")
                yield (b, a, out_date, None, f"{b}→{a}")


def run(cfg: dict, limit: int | None = None, verbose: bool = True) -> dict:
    ts = dt.datetime.now().isoformat(timespec="seconds")
    results = {"抓取時間": ts, "round-trip": [], "one-way": []}
    delay = cfg.get("每次請求間隔秒數", [3, 6])
    if verbose:
        nd = len(_candidate_dates(cfg))
        est = sum(len(list(_combos(cfg, t))) for t in cfg.get("抓取模式", ["round-trip"]))
        print(f"候選日 {nd} 組,預計查詢 {est} 次(越多越慢也越容易被擋)")
    n = 0
    for trip in cfg.get("抓取模式", ["round-trip"]):
        for (frm, to, od, rd, route) in _combos(cfg, trip):
            if limit and n >= limit:
                break
            n += 1
            try:
                cards = _query(frm, to, od, rd, trip, cfg)
            except Exception as e:
                if verbose:
                    print(f"  ! {route} {od} 失敗: {type(e).__name__}")
                cards = []
            for c in cards:
                c.update({"route": route, "out_date": od, "ret_date": rd, "trip": trip})
            results[trip].extend(cards)
            if verbose:
                best = min((c["price"] for c in cards if c["price"] is not None), default=None)
                print(f"  [{trip}] {route} 去{od}" + (f"/回{rd}" if rd else "")
                      + f" -> {len(cards)} 筆" + (f",最低 NT${best:,}" if best else ""))
            time.sleep(random.uniform(*delay))
    return results


def save(results: dict):
    SNAPSHOT.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    hist = []
    if HISTORY.exists():
        hist = json.loads(HISTORY.read_text())
    # 歷史只存每個 (模式,路線,日期) 當次最低價,保持精簡
    snap = {"時間": results["抓取時間"], "最低": {}}
    for trip in ("round-trip", "one-way"):
        for c in results[trip]:
            if c["price"] is None:  # 無價格的班次不計入歷史最低
                continue
            key = f'{trip}|{c["route"]}|{c["out_date"]}|{c.get("ret_date") or ""}'
            if key not in snap["最低"] or c["price"] < snap["最低"][key]["price"]:
                snap["最低"][key] = {"price": c["price"], "airline": c["airline"]}
    hist.append(snap)
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys
    cfg = json.loads((ROOT / "config.json").read_text())
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    res = run(cfg, limit=limit)
    save(res)
    print(f"\n完成。來回 {len(res['round-trip'])} 筆、單程 {len(res['one-way'])} 筆,已寫入 data.json / history.json")
