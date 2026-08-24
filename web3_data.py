"""Ambil data pasar / trending Web3 dari CoinGecko + Fear & Greed (API publik, tanpa key)."""
import requests
import xml.etree.ElementTree as ET

CG_BASE = "https://api.coingecko.com/api/v3"
FNG_URL = "https://api.alternative.me/fng/?limit=1"
BINANCE_FUNDING = "https://fapi.binance.com/fapi/v1/premiumIndex"
DEFILLAMA_TVL = "https://api.llama.fi/v2/historicalChainTvl"
NEWS_RSS = "https://cointelegraph.com/rss"
HEADERS = {"Accept": "application/json", "User-Agent": "web3-news-bot/1.0"}
TIMEOUT = 20


def _get(url, **params):
    r = requests.get(url, headers=HEADERS, params=params or None, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_global():
    """Statistik pasar global: total market cap, perubahan 24j, dominasi BTC/ETH, volume."""
    data = _get(f"{CG_BASE}/global").get("data", {})
    tmc = data.get("total_market_cap", {})
    tv = data.get("total_volume", {})
    dom = data.get("market_cap_percentage", {})
    return {
        "total_mcap": tmc.get("usd"),
        "mcap_change_24h": data.get("market_cap_change_percentage_24h_usd"),
        "volume": tv.get("usd"),
        "btc_dom": dom.get("btc"),
        "eth_dom": dom.get("eth"),
    }


def get_fear_greed():
    """Crypto Fear & Greed Index (0-100) dari alternative.me."""
    try:
        d = _get(FNG_URL)["data"][0]
        return {"value": int(d["value"]), "label": d["value_classification"]}
    except Exception:  # noqa: BLE001
        return None


def get_trending():
    """Koin yang sedang trending (paling banyak dicari) di CoinGecko."""
    coins = _get(f"{CG_BASE}/search/trending").get("coins", [])
    out = []
    for c in coins[:7]:
        item = c.get("item", {})
        data = item.get("data", {}) or {}
        out.append({
            "name": item.get("name"),
            "symbol": (item.get("symbol") or "").upper(),
            "rank": item.get("market_cap_rank"),
            "change_24h": (data.get("price_change_percentage_24h") or {}).get("usd"),
        })
    return out


def get_markets(per_page=100):
    """Ambil koin berdasarkan market cap + perubahan harga 24 jam."""
    rows = _get(
        f"{CG_BASE}/coins/markets",
        vs_currency="usd", order="market_cap_desc",
        per_page=per_page, page=1, price_change_percentage="24h",
    )
    return [{
        "name": c.get("name"),
        "symbol": (c.get("symbol") or "").upper(),
        "price": c.get("current_price"),
        "change_24h": c.get("price_change_percentage_24h"),
        "market_cap": c.get("market_cap"),
        "volume": c.get("total_volume"),
    } for c in rows]


def get_gainers_losers(markets):
    """Top 5 gainers & losers 24j dari daftar market (yang punya data perubahan)."""
    valid = [m for m in markets if m.get("change_24h") is not None]
    gainers = sorted(valid, key=lambda m: m["change_24h"], reverse=True)[:5]
    losers = sorted(valid, key=lambda m: m["change_24h"])[:5]
    return gainers, losers


def get_funding_rates():
    """Funding rate perpetual BTC & ETH dari Binance Futures (sinyal sentimen leverage)."""
    try:
        out = {}
        for sym, key in (("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")):
            r = requests.get(BINANCE_FUNDING, params={"symbol": sym},
                             headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            out[key] = float(r.json()["lastFundingRate"]) * 100  # ke persen
        return out
    except Exception:  # noqa: BLE001
        return None


def get_defi_tvl():
    """Total TVL DeFi terkini + perubahannya kira-kira 24 jam dari DefiLlama."""
    try:
        data = requests.get(DEFILLAMA_TVL, headers=HEADERS, timeout=TIMEOUT).json()
        if not data:
            return None
        now = data[-1]["tvl"]
        prev = data[-2]["tvl"] if len(data) > 1 else now
        change = ((now - prev) / prev * 100) if prev else None
        return {"tvl": now, "change": change}
    except Exception:  # noqa: BLE001
        return None


def get_news_headlines(limit=5):
    """Judul berita kripto terbaru dari RSS Cointelegraph."""
    try:
        r = requests.get(NEWS_RSS, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        titles = []
        for item in root.iter("item"):          # hanya <item>, lewati judul channel/image
            t = item.find("title")
            if t is not None and t.text:
                titles.append(t.text.strip())
            if len(titles) >= limit:
                break
        return titles
    except Exception:  # noqa: BLE001
        return []


def _fmt_price(p):
    if p is None:
        return "-"
    if p >= 1:
        return f"${p:,.2f}"
    return f"${p:,.6f}".rstrip("0").rstrip(".")


def _fmt_big(n):
    if n is None:
        return "-"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if n >= div:
            return f"${n / div:.2f}{unit}"
    return f"${n:,.0f}"


def _pct(x):
    return f"{x:+.2f}%" if x is not None else "N/A"


def build_market_summary():
    """Rangkum semua data mentah menjadi teks kaya konteks untuk AI. Return (teks, dict data)."""
    glob = get_global()
    fng = get_fear_greed()
    trending = get_trending()
    markets = get_markets(100)
    gainers, losers = get_gainers_losers(markets)
    funding = get_funding_rates()
    tvl = get_defi_tvl()
    news = get_news_headlines(5)
    top = markets[:8]

    L = ["=== KONDISI PASAR GLOBAL ==="]
    L.append(f"- Total market cap kripto: {_fmt_big(glob['total_mcap'])} ({_pct(glob['mcap_change_24h'])} 24j)")
    L.append(f"- Volume perdagangan 24j: {_fmt_big(glob['volume'])}")
    L.append(f"- Dominasi BTC: {glob['btc_dom']:.1f}% | ETH: {glob['eth_dom']:.1f}%")
    if fng:
        L.append(f"- Fear & Greed Index: {fng['value']}/100 ({fng['label']})")
    if tvl:
        L.append(f"- Total TVL DeFi: {_fmt_big(tvl['tvl'])} ({_pct(tvl['change'])} 24j)")
    if funding:
        L.append(f"- Funding rate perpetual — BTC: {_pct(funding.get('BTC'))}, "
                 f"ETH: {_pct(funding.get('ETH'))} (positif = dominasi long)")

    L.append("\n=== KOIN TRENDING (paling dicari) ===")
    for t in trending:
        rank = f"rank #{t['rank']}" if t["rank"] else "rank N/A"
        L.append(f"- {t['name']} ({t['symbol']}), {rank}, 24j: {_pct(t.get('change_24h'))}")

    L.append("\n=== TOP GAINERS 24J (dari 100 besar) ===")
    for g in gainers:
        L.append(f"- {g['name']} ({g['symbol']}): {_fmt_price(g['price'])} | {_pct(g['change_24h'])}")

    L.append("\n=== TOP LOSERS 24J (dari 100 besar) ===")
    for lo in losers:
        L.append(f"- {lo['name']} ({lo['symbol']}): {_fmt_price(lo['price'])} | {_pct(lo['change_24h'])}")

    L.append("\n=== TOP MARKET CAP ===")
    for m in top:
        L.append(f"- {m['name']} ({m['symbol']}): {_fmt_price(m['price'])} | 24j: {_pct(m['change_24h'])}")

    if news:
        L.append("\n=== HEADLINE BERITA KRIPTO TERBARU ===")
        for h in news:
            L.append(f"- {h}")

    data = {
        "global": glob, "fear_greed": fng, "trending": trending,
        "gainers": gainers, "losers": losers, "top": top,
        "funding": funding, "tvl": tvl, "news": news,
    }
    return "\n".join(L), data
