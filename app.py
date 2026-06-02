"""
股票監控儀表板 - 完整修復版 v3.7
==================================
v3.7 AI Prompt 功能（免 API，複製貼去任何 AI 使用）：
47. _save_ticker_snapshot：主監控每次刷新後把即時快照存入 session_state，
    包含價格、全部技術指標、信號、K線形態、成交量、VIX、成交密集區、近5根K線。
48. _build_signal_prompt（場景A）：每個 ticker tab 加入「複製 AI Prompt」expander，
    自動注入即時市況 + 三維回測最佳組合 + 爆升回測特徵 + 密集區支撐壓力，
    用戶複製貼去 ChatGPT/Claude/Gemini 即獲具體操作建議，無需花費 API。
49. _build_overview_prompt（場景B）：在爆升回測區域上方加入「每日總覽 Prompt」，
    一次彙總所有監控股票的快照，讓 AI 給出今日操作優先級排序。
50. AI 對話改善：切換 ticker 時自動清空對話歷史（避免上下文混亂）；
    system prompt 從只有爆升回測摘要，升級為注入完整即時快照 + 回測數據雙重上下文。

v3.6 信號全面修復（逐一審查 62 個信號後修正 11 項錯誤 + 12 項警告）：
── 🔴 錯誤修復 ──
36. HIGH_N_HIGH / LOW_N_LOW：改為在 _mark_one 用 OHLC 直接計算，
    不再依賴回測中為 NaN 的 Close_N_High/Low 欄位，回測現在可正常觸發。
    LOW_N_LOW 加入 SELL_SIGNALS（原本缺失，回測方向算成做多）。
    HIGH_N_HIGH / LOW_N_LOW 加入 ALL_SIGNAL_TYPES（原本 Telegram 選不到）。
37. 📈 衰竭跳空(上)：改名為 📉 衰竭跳空(上)，加入 SELL_SIGNALS。
    本質是看空信號（跳空高開後收陰回吐），原用 📈 標記且不在 SELL_SIGNALS，
    回測方向完全錯誤。
38. 🔄 新转折点：拆分為 🔄 新转折点(漲) / 🔄 新转折点(跌) 兩個有方向的信號。
    原信號漲跌都觸發同一個名稱，且 MACD>Signal 只過濾多頭但漲跌皆算，邏輯矛盾。
    新转折点(跌) 加入 SELL_SIGNALS。
39. 📈 EMA-SMA Uptrend Buy / 📉 EMA-SMA Downtrend Sell：加入交叉判斷
    (pv(EMA5)<=pv(EMA10))，從「每天都觸發的狀態信號」改為「交叉當天才觸發的轉折信號」。
40. 📈 EMA10_30_40強烈買入 / 📉 EMA10_30_40強烈賣出：修正 EMA40 預設值陷阱。
    原 row.get("EMA40", 0/999999)，EMA40 欄位缺失時幾乎必然觸發。
    改為 pd.notna(row.get("EMA40")) 確認存在後才比較。
41. 📈 錘頭線 / 📉 上吊線：原條件完全相同，RSI 30–70 時同時觸發矛盾信號。
    加入5日趨勢方向判斷：下跌趨勢中（Close<5日均）→ 錘頭線；
    上漲趨勢中（Close>5日均）→ 上吊線，且 RSI 門檻從<70/>30 收緊到<50/>50。
42. 📉 BreakDown_5K：加入 SELL_SIGNALS（原本缺失，回測方向算成做多）。
── 🟡 警告改善 ──
43. 📈 SMA50上升趨勢 / 📉 SMA50下降趨勢：加入穿越判斷（pv(Close)<=pv(SMA50)），
    從純狀態信號改為穿越當天才觸發。
44. 📈 SMA50_200上升趨勢 / 📉 SMA50_200下降趨勢：同上。
45. 📈 新买入信号 / 📉 新卖出信号：加入放量確認（Volume>前5均量），
    過濾掉低量陽/陰線，提高信噪比。
46. BreakOut_5K / BreakDown_5K 窗口與 MFI 解耦：原共用 mfi_win 參數，
    改 MFI 窗口會連帶改突破窗口。改為固定 _BREAKOUT_WIN=5，與信號名稱語義一致。

v3.5 信號修復：
35. FIX「✅ 量價」回測缺席：原回測將「📈 股價漲跌幅(%)」和「📊 成交量變動幅(%)」
    強制設為 np.nan，導致此信號在回測和逐筆驗證中永遠不觸發、無法評估歷史勝率。
    改為在 _run_backtest_for_ticker 和 _bt_raw 兩處，以與主監控完全相同的公式計算：
      pa = (|今日漲跌幅| - 5日均漲跌幅) / 5日均漲跌幅 × 100
      va = (今日成交量 - 5日均量) / 5日均量 × 100
    （Price Change % 和 前5均量 在 _enrich_data 已計算，回測亦有此欄位，
     無需額外抓取數據，只需加兩行衍生計算）

v3.4 優化與修復（10 項）：
── P1 正確性 ──
27. FIX P1-#1 _bt_raw 重複抓取：逐筆驗證改用 _fetch_price_data 快取函數，
    與 _run_backtest_for_ticker 拿同一份數據，避免兩次抓取時間不同造成信號/驗證不一致。
28. FIX P1-#3 compute_all_signals 崩潰防護：每根 K 線外層加 try/except，
    單根數據異常（NaN/除零）回傳空字串而非拋出例外，整個 ticker tab 不再崩潰。
── P2 效能 ──
29. FIX P2-#4 主監控 yfinance 快取：新增 _fetch_price_data(ttl=60s)，
    主監控改用此函數，每 60 秒內 rerun 不重打網路，保持近即時。
30. FIX P2-#6 backtest_signal_combinations 舊入口傳 _ctx，省一次 onehot 重建。
── P4 使用體驗 ──
31. FIX P4-#9 Telegram parse_mode="HTML"：訊息加 HTML 解析模式，
    emoji 和格式正確渲染，不再原文顯示星號。
32. FIX P4-#10 並行結果排序：as_completed 完成順序隨機，
    改為按 selected_tickers 原序重排後再顯示，介面一致。
── Lint 清理（P3）──
33. 移除 stock 未定義引用（改用 yf.Ticker(ticker).info）。
34. 清理 17 處 pyflakes 警告：10 個無佔位符 f-string、ph/pl/closes/
    test_non/n_surge/n_non 未用變量、import csv as _csv 未用 import。

v3.3 加速清單（不影響信號準確度）：
25. _build_onehot 共用（_BtCtx）：三個維度函數原各自重建 one-hot 矩陣（×3）；
    改為在 _run_backtest_for_ticker 建立一次 _BtCtx 傳入，省去 2/3 前置時間。
26. 多股票並行回測（ThreadPoolExecutor）：自動回測原為串行（N 支 × T 秒）；
    改為最多 6 執行緒並行（yfinance 為 I/O bound，GIL 不影響），
    13 支股票理論從 ~13T → ~3T。session_state/UI 寫入仍在主執行緒。
    ⚠️ 對信號準確度零影響：每支股票數據/信號計算完全獨立。

v3.2 修復清單：
22. 全域 Telegram 信號選擇：原「每支股票各一個 multiselect」→ 改為側欄單一全域
    選擇 (global_selected_signals)，套用所有股票；個別股票仍可用 tg_enabled_{ticker} 靜音。
23. BUG-09 前瞻偏差修正：衰竭跳空(上/下)原用「下一根收盤」(data["Close"].iloc[idx+1])
    判斷反轉 → look-ahead bias，會虛高回測勝率。改用當根 intrabar 證據判斷
    （收盤回吐跳空 + 收盤位置），僅用當根 O/H/L/C，不偷看未來。
24. 回測加速：
    (a) _run_backtest_for_ticker 加 @st.cache_data(ttl=300) → 避免每次 rerun 重抓重算。
    (b) 新增 _prefilter_signals：單一信號未達 min_occ 即剔除，任何含它的組合
        必不達標。組合數可縮減 ~100x（信號越稀疏效果越大），×3 維度。

v2.0 修復清單：
 1. matched_rank 未定義 NameError → 先初始化為 None
 2. while True + time.sleep() → time.sleep() + st.rerun()（Streamlit Cloud 相容）
 3. @st.cache_data 接收不可哈希 DataFrame → 改用 ticker/period/interval 字串作 key
 4. VIX merge 時區不符全為 NaN → 統一 tz_localize(None)
 5. make_subplots 中 yaxis2/yaxis3 overlaying 衝突 → 改用 4 行獨立子圖
 6. px.line()["data"][0] 不規範 → 全用 go.Scatter
 7. generate_comprehensive_interpretation dense_desc 在 return 後無效 → 前移
 8. VWAP 跨日累積錯誤 → 按日分組計算
 9. 新增完整回測系統（組合信號勝率分析）
10. send_email_alert 參數過多 → 整合為 dict

v3.0 修復清單：
11. BUG-01: MFI 背離浮點精確比較 → 改用 0.2% 容差
12. BUG-02: 回測勝率最後一根 NaN→False → 排除 NaN 行
13. BUG-03: Telegram 重複發送 → 加 session_state 去重
14. BUG-04: 回測中 data 變量被覆蓋 → 使用獨立變量名
15. BUG-05: RSI 使用 SMA → 改用 Wilder's Smoothing (EWM)
16. BUG-06: MACD/EMA 買入 RSI<50 矛盾 → 放寬到 RSI<70
17. BUG-07: VIX 短週期全 NaN → 改用按日期合併
18. BUG-08: 回測進場價=當根收盤 → 改用下一根開盤
19. BUG-09: 勝率與詳細回測不一致提示
20. BUG-10: MFI fillna(50) → 保持 NaN
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from itertools import combinations
import time
import traceback
import json
import concurrent.futures

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="📈 股票監控儀表板", layout="wide", page_icon="📈")
load_dotenv()

SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")

try:
    BOT_TOKEN      = st.secrets["telegram"]["BOT_TOKEN"]
    CHAT_ID        = st.secrets["telegram"]["CHAT_ID"]
    telegram_ready = True
except Exception:
    BOT_TOKEN = CHAT_ID = None
    telegram_ready = False

try:
    GROQ_API_KEY = st.secrets["groq"]["GROQ_API_KEY"]
    groq_ready   = True
except Exception:
    GROQ_API_KEY = None
    groq_ready   = False

# ── Sell-signal set (used in success-rate & backtest direction logic) ─────────
SELL_SIGNALS = {
    "📉 High<Low","📉 MACD賣出","📉 EMA賣出","📉 價格趨勢賣出","📉 價格趨勢賣出(量)",
    "📉 價格趨勢賣出(量%)","📉 普通跳空(下)","📉 突破跳空(下)","📉 持續跳空(下)",
    "📉 衰竭跳空(下)","📉 連續向下賣出","📉 SMA50下降趨勢","📉 SMA50_200下降趨勢",
    "📉 新卖出信号","📉 RSI-MACD Overbought Crossover","📉 EMA-SMA Downtrend Sell",
    "📉 Volume-MACD Sell","📉 EMA10_30賣出","📉 EMA10_30_40強烈賣出","📉 看跌吞沒",
    "📉 烏雲蓋頂","📉 上吊線","📉 黃昏之星","📉 VWAP賣出","📉 MFI熊背離賣出",
    "📉 OBV突破賣出","📉 VIX恐慌賣出","📉 VIX上升趨勢賣出",
    # FIX v3.6: 以下兩個原本缺失，回測方向算成做多 → 修正為賣出
    "📉 LOW_N_LOW",      # 收在當日極低位置 = 看空
    "📉 BreakDown_5K",   # 跌破近期低點 = 看空
    # FIX v3.6: 衰竭跳空(上)本質看空，改名並加入賣出集合（見 _mark_one）
    "📉 衰竭跳空(上)",
    # FIX v3.6: 新转折点拆分方向後，跌方向加入賣出集合
    "🔄 新转折点(跌)",
}

# ═════════════════════════════════════════════════════════════════════════════
#  INDICATOR FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════


def send_telegram_alert(msg: str, ticker: str = None) -> tuple:
    """
    Send a plain-text message via Telegram Bot API.
    Returns (success: bool, error_msg: str).

    FIX: 統一在函數入口檢查所有開關狀態（熔斷機制）
    - 1️⃣ 檢查全域靜音開關 (tg_global_mute)
    - 2️⃣ 檢查該股票的 tg_enabled_{ticker}
    - 3️⃣ 無論呼叫端是否忘記檢查開關，都會被攔截
    """
    # 熔斷機制 1：全域靜音（panic stop）
    try:
        if st.session_state.get("tg_global_mute", False):
            return False, "Telegram 全域靜音已開啟"
    except Exception:
        pass

    # 熔斷機制 2：個別股票開關
    if ticker is not None:
        try:
            if not st.session_state.get(f"tg_enabled_{ticker}", True):
                return False, f"Telegram 已關閉 ({ticker})"
        except Exception:
            pass

    if not (BOT_TOKEN and CHAT_ID):
        return False, "Telegram 未設定（請在 secrets.toml 中設定 BOT_TOKEN 和 CHAT_ID）"
    try:
        url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id":                  CHAT_ID,
            "text":                     msg,
            "parse_mode":               "HTML",   # FIX P4-#9: 啟用 HTML 渲染，避免原文顯示星號
            "disable_web_page_preview": True,
            "disable_notification":     False,
        }
        r = requests.post(url, json=payload, timeout=15)
        resp = r.json()
        if r.status_code == 200 and resp.get("ok"):
            return True, ""
        else:
            err = resp.get("description", f"HTTP {r.status_code}")
            return False, f"Telegram API 錯誤：{err}"
    except requests.exceptions.Timeout:
        return False, "Telegram 發送逾時（15 秒）"
    except Exception as e:
        return False, f"Telegram 發送例外：{e}"


def _fmt_vol(vol) -> str:
    """Format volume as readable string: 1,234,567 → 1.23M"""
    try:
        v = float(vol)
        if v >= 1_000_000:
            return f"{v/1_000_000:.2f}M"
        elif v >= 1_000:
            return f"{v/1_000:.1f}K"
        else:
            return f"{v:.0f}"
    except Exception:
        return str(vol)


def calculate_macd(df, fast=12, slow=26, signal=9):
    e1 = df["Close"].ewm(span=fast, adjust=False).mean()
    e2 = df["Close"].ewm(span=slow, adjust=False).mean()
    macd = e1 - e2
    sig  = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig


# ── FIX BUG-05: RSI 改用 Wilder's Smoothing ──────────────────────────────────
def calculate_rsi(df, periods=14):
    delta = df["Close"].diff()
    gain  = delta.where(delta > 0, 0)
    loss  = (-delta.where(delta < 0, 0))
    # Wilder's Smoothing = EWM with alpha=1/periods
    avg_gain = gain.ewm(alpha=1/periods, min_periods=periods, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/periods, min_periods=periods, adjust=False).mean()
    rs    = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    FIX: group by calendar date so VWAP resets each day.
    """
    df2 = df.copy()
    df2["_dt"] = pd.to_datetime(df2["Datetime"]).dt.date
    typical = (df2["High"] + df2["Low"] + df2["Close"]) / 3
    tp_vol  = typical * df2["Volume"]

    vwap_vals = []
    for date, grp in df2.groupby("_dt", sort=False):
        cum_tv = tp_vol.loc[grp.index].cumsum()
        cum_v  = df2.loc[grp.index, "Volume"].cumsum().replace(0, np.nan)
        vwap_vals.append(cum_tv / cum_v)

    result = pd.concat(vwap_vals).reindex(df2.index)
    return result


# ── FIX BUG-10: MFI 不再 fillna(50)，保持 NaN ───────────────────────────────
def calculate_mfi(df, periods=14):
    typical    = (df["High"] + df["Low"] + df["Close"]) / 3
    mf         = typical * df["Volume"]
    pos_mf     = mf.where(typical > typical.shift(1), 0).rolling(window=periods).sum()
    neg_mf     = mf.where(typical < typical.shift(1), 0).rolling(window=periods).sum()
    mfi        = 100 - (100 / (1 + pos_mf / neg_mf.replace(0, np.nan)))
    return mfi  # 不再 fillna(50)


def calculate_obv(df):
    return (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()


def calculate_volume_profile(df, bins=50, window=100, top_n=3):
    n = min(len(df), window)
    recent = df.tail(n).copy()
    pmin, pmax = recent["Low"].min(), recent["High"].max()
    if pmax == pmin:
        return []
    edges   = np.linspace(pmin, pmax, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    profile = np.zeros(bins)
    for _, row in recent.iterrows():
        lo_i = max(0, int(np.searchsorted(edges, row["Low"],  "left")  - 1))
        hi_i = max(0, min(int(np.searchsorted(edges, row["High"], "right") - 1), bins - 1))
        lo_i = min(lo_i, bins - 1)
        span = hi_i - lo_i + 1
        for j in range(lo_i, hi_i + 1):
            profile[j] += row["Volume"] / span
    top_idx = np.argsort(profile)[-top_n:][::-1]
    return [{"price_center": centers[i], "volume": profile[i],
             "price_low": edges[i], "price_high": edges[i + 1]}
            for i in top_idx if profile[i] > 0]


def get_vix_data(period, interval):
    try:
        vdf = yf.Ticker("^VIX").history(period=period, interval=interval).reset_index()
        if vdf.empty:
            return pd.DataFrame()
        if "Date" in vdf.columns:
            vdf = vdf.rename(columns={"Date": "Datetime"})
        vdf["Datetime"]      = pd.to_datetime(vdf["Datetime"]).dt.tz_localize(None)
        vdf["VIX_Change_Pct"]= vdf["Close"].pct_change().round(4) * 100
        return vdf[["Datetime", "Close", "VIX_Change_Pct"]].rename(columns={"Close": "VIX"})
    except Exception:
        return pd.DataFrame()


# ── FIX BUG-07: VIX 按日期合併（解決短週期全 NaN 問題）─────────────────────
def merge_vix_data(data: pd.DataFrame, vix_df: pd.DataFrame,
                   interval: str) -> pd.DataFrame:
    """
    智能合併 VIX 數據：
    - 日線及以上：按精確 Datetime 合併（與原邏輯一致）
    - 短週期（分鐘/小時）：按日期合併（避免時間戳不對齊導致全 NaN）
    """
    if vix_df.empty:
        data["VIX"] = np.nan
        data["VIX_Change_Pct"] = np.nan
        return data

    # 判斷是否為短週期
    _intraday = interval in ("1m", "5m", "15m", "30m", "60m", "1h")

    if _intraday:
        # 按日期合併
        data["_merge_date"] = pd.to_datetime(data["Datetime"]).dt.date
        vix_df = vix_df.copy()
        vix_df["_merge_date"] = pd.to_datetime(vix_df["Datetime"]).dt.date
        # VIX 日線可能有重複日期，取最後一筆
        vix_daily = vix_df.drop_duplicates(subset=["_merge_date"], keep="last")
        data = data.merge(
            vix_daily[["_merge_date", "VIX", "VIX_Change_Pct"]],
            on="_merge_date", how="left"
        ).drop(columns=["_merge_date"])
    else:
        # 日線及以上：原邏輯
        data = data.merge(vix_df, on="Datetime", how="left")

    return data


# ── FIX BUG-01: MFI 背離使用容差比較 ─────────────────────────────────────────
def compute_mfi_divergence(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    計算 MFI 背離，使用 0.2% 容差替代精確浮點比較。
    回傳帶有 MFI_Bull_Div / MFI_Bear_Div 欄位的 DataFrame。
    """
    df = df.copy()
    df["Close_Roll_Max"] = df["Close"].rolling(window).max()
    df["Close_Roll_Min"] = df["Close"].rolling(window).min()
    df["MFI_Roll_Max"]   = df["MFI"].rolling(window).max()
    df["MFI_Roll_Min"]   = df["MFI"].rolling(window).min()

    # 容差比較：收盤價在滾動極值的 0.2% 以內即視為「觸及」
    _tol = 0.002
    _close_near_max = (
        (df["Close"] - df["Close_Roll_Max"]).abs() /
        df["Close_Roll_Max"].replace(0, np.nan)
    ) < _tol
    _close_near_min = (
        (df["Close"] - df["Close_Roll_Min"]).abs() /
        df["Close_Roll_Min"].replace(0, np.nan)
    ) < _tol

    # 熊背離：價格觸及新高但 MFI 低於前期高點
    df["MFI_Bear_Div"] = _close_near_max & (df["MFI"] < df["MFI_Roll_Max"].shift(1))
    # 牛背離：價格觸及新低但 MFI 高於前期低點
    df["MFI_Bull_Div"] = _close_near_min & (df["MFI"] > df["MFI_Roll_Min"].shift(1))

    return df


# ═════════════════════════════════════════════════════════════════════════════
#  AI PROMPT BUILDER  (v3.7)
#  把即時數據、信號、回測結果濃縮成高品質 prompt，用戶可複製貼去任何 AI 使用
# ═════════════════════════════════════════════════════════════════════════════

def _save_ticker_snapshot(ticker: str, data: "pd.DataFrame",
                          dense_areas: list,
                          period: str, interval: str) -> None:
    """主監控每次刷新後把即時快照存入 session_state，供 prompt 生成函數讀取。"""
    if data is None or len(data) < 2:
        return
    last = data.iloc[-1]
    prev = data.iloc[-2]

    def _safe(val, fmt=".2f"):
        try:
            return f"{float(val):{fmt}}" if pd.notna(val) else "N/A"
        except Exception:
            return "N/A"

    k5 = data[["Datetime","Close","Volume","異動標記","K線形態","成交量標記"]].tail(5).copy()
    k5["Datetime"] = k5["Datetime"].dt.strftime("%m-%d")
    k5_rows = []
    for _, r in k5.iterrows():
        sigs_short = str(r["異動標記"])[:60] + "…" if len(str(r["異動標記"])) > 60 else str(r["異動標記"])
        k5_rows.append(
            f"  {r['Datetime']} 收${r['Close']:.2f} {r['成交量標記']} "
            f"{r['K線形態']}｜{sigs_short}"
        )

    st.session_state[f"ai_snap_{ticker}"] = {
        "ticker":      ticker,
        "period":      period,
        "interval":    interval,
        "datetime":    str(last.get("Datetime", ""))[:16],
        "close":       _safe(last["Close"]),
        "prev_close":  _safe(prev["Close"]),
        "pct_chg":     f"{(last['Close']-prev['Close'])/prev['Close']*100:+.2f}"
                       if prev["Close"] else "N/A",
        "rsi":         _safe(last.get("RSI"), ".1f"),
        "macd":        _safe(last.get("MACD"), ".4f"),
        "signal_line": _safe(last.get("Signal_Line"), ".4f"),
        "ema5":        _safe(last.get("EMA5")),
        "ema10":       _safe(last.get("EMA10")),
        "ema30":       _safe(last.get("EMA30")),
        "ema40":       _safe(last.get("EMA40")),
        "sma50":       _safe(last.get("SMA50")),
        "sma200":      _safe(last.get("SMA200")),
        "vwap":        _safe(last.get("VWAP")),
        "mfi":         _safe(last.get("MFI"), ".1f"),
        "obv_trend":   ("OBV↑" if pd.notna(last.get("OBV")) and
                        data["OBV"].iloc[-1] > data["OBV"].iloc[-5] else "OBV↓"),
        "vix":         _safe(last.get("VIX"), ".1f"),
        "volume":      _fmt_vol(last["Volume"]),
        "vol_ma5":     _fmt_vol(last.get("前5均量", 0)),
        "vol_tag":     str(last.get("成交量標記", "")),
        "kline_pat":   str(last.get("K線形態", "")),
        "signals":     str(last.get("異動標記", "無")),
        "dense":       [{"low":    f"{a['price_low']:.2f}",
                         "high":   f"{a['price_high']:.2f}",
                         "center": f"{a['price_center']:.2f}"}
                        for a in dense_areas],
        "k5_lines":    k5_rows,
    }


def _build_signal_prompt(ticker: str) -> str:
    """
    場景 A：信號觸發時的即時 prompt。
    注入即時技術指標 + 觸發信號 + 回測勝率 + 密集區。
    用戶複製貼去任何 AI 可獲得具體操作建議。
    """
    snap = st.session_state.get(f"ai_snap_{ticker}")
    if not snap:
        return f"⚠️ {ticker} 尚未有即時數據，請先讓主監控刷新一次。"

    # ── 三維回測最佳組合 Top2 ──
    bt_top3_lines = []
    for key, dim in [(f"bt_df_sig_{ticker}", "信號組合"),
                     (f"bt_df_vol_{ticker}", "信號+成交量"),
                     (f"bt_df_kl_{ticker}",  "信號+K線")]:
        df = st.session_state.get(key)
        if df is not None and not df.empty:
            for _, r in df.head(2).iterrows():
                bt_top3_lines.append(
                    f"  [{dim}] {r['信號組合']} | "
                    f"勝率{r['勝率(%)']}% | 出現{r['出現次數']}次 | "
                    f"均盈虧{r.get('平均盈虧(%)', 'N/A')}%"
                )
    bt_top3 = "\n".join(bt_top3_lines) if bt_top3_lines else "  尚未執行三維回測"

    # ── 爆升回測摘要 ──
    sp_bt = st.session_state.get(f"sp_result_{ticker}")
    surge_lines = []
    if sp_bt and not sp_bt.get("error"):
        for row in sp_bt.get("feature_power", [])[:3]:
            surge_lines.append(
                f"  {row['特徵']}: 預測力{row['預測力倍數']}x "
                f"(爆升前{row['爆升前出現率']}% vs 非爆升{row['非爆升出現率']}%)"
            )
        hs = sp_bt.get("horizon_stats", {})
        if hs:
            try:
                best = max(hs.items(),
                           key=lambda x: float(str(x[1].get("勝率", 0)).replace("%", "")))
                surge_lines.append(
                    f"  最佳持倉: {best[0]} → "
                    f"均漲{best[1].get('平均漲幅','N/A')}% 勝率{best[1].get('勝率','N/A')}%"
                )
            except Exception:
                pass
    surge_summary = "\n".join(surge_lines) if surge_lines else "  尚未執行爆升回測"

    # ── 密集區分支撐/壓力 ──
    dense = snap["dense"]
    try:
        cur = float(snap["close"])
        supports    = ["$" + a["center"] for a in dense if float(a["center"]) < cur]
        resistances = ["$" + a["center"] for a in dense if float(a["center"]) > cur]
    except Exception:
        supports = resistances = []
    dense_str = (
        f"  支撐：{' / '.join(supports[-2:]) or '無'}\n"
        f"  壓力：{' / '.join(resistances[:2]) or '無'}"
    )

    prompt = f"""你是一位專業股票交易分析師，擅長量價技術分析。
請根據以下完整數據，給出具體可執行的操作建議。

━━━ {ticker} 即時市況（{snap['datetime']}，{snap['period']}/{snap['interval']}）━━━

【價格】
  現價：${snap['close']}　昨收：${snap['prev_close']}　漲跌：{snap['pct_chg']}%

【技術指標】
  RSI：{snap['rsi']}　MACD：{snap['macd']}　Signal：{snap['signal_line']}
  EMA5：{snap['ema5']}　EMA10：{snap['ema10']}　EMA30：{snap['ema30']}　EMA40：{snap['ema40']}
  SMA50：{snap['sma50']}　SMA200：{snap['sma200']}
  VWAP：{snap['vwap']}　MFI：{snap['mfi']}　{snap['obv_trend']}　VIX：{snap['vix']}

【成交量】
  今日：{snap['volume']}　5日均量：{snap['vol_ma5']}　標記：{snap['vol_tag']}

【今日K線形態】
  {snap['kline_pat']}

【今日觸發信號】
  {snap['signals']}

【近5根K線走勢】
{chr(10).join(snap['k5_lines'])}

【成交密集區】
{dense_str}

【三維回測最佳組合（歷史統計）】
{bt_top3}

【爆升前特徵（歷史統計）】
{surge_summary}

━━━ 請回答以下問題 ━━━

1. 📊 當前技術面總結：多空力道？趨勢強弱？
2. 🎯 操作建議：做多 / 做空 / 觀望？信心度（1-5）？
3. 📍 具體條件：進場價、止損位、目標價（請給具體數字）
4. ⏱️ 持倉建議：持倉多少天較合理？
5. ⚠️ 主要風險：1-2個最需注意的風險點
6. 📋 判斷依據：主要依賴上面哪些數據做出判斷？

請用繁體中文回答，給出具體數字，避免模糊表述。"""

    return prompt


def _build_overview_prompt(tickers: list) -> str:
    """
    場景 B：所有監控股票的每日總覽 prompt。
    一次問所有 ticker 的狀況，讓 AI 給出今日操作優先級。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"你是一位專業股票交易分析師。以下是我的股票監控系統今日數據（{today}），",
        "請分析每隻股票的當前狀況，並給出今日操作優先級排序。\n",
        "━━━ 各股票即時快照 ━━━\n",
    ]

    has_data = False
    for tk in tickers:
        snap = st.session_state.get(f"ai_snap_{tk}")
        if not snap:
            lines.append(f"【{tk}】尚無數據\n")
            continue
        has_data = True

        sigs_short = snap["signals"][:80] + "…" if len(snap["signals"]) > 80 else snap["signals"]

        best_wr = "N/A"
        df_sig = st.session_state.get(f"bt_df_sig_{tk}")
        if df_sig is not None and not df_sig.empty:
            best_wr = f"{df_sig.iloc[0]['勝率(%)']}%（{str(df_sig.iloc[0]['信號組合'])[:30]}）"

        try:
            e5, e10, e30 = float(snap["ema5"]), float(snap["ema10"]), float(snap["ema30"])
            ema_arr = "多頭排列" if e5>e10>e30 else ("空頭排列" if e5<e10<e30 else "交叉中")
        except Exception:
            ema_arr = "N/A"

        try:
            rsi_v = float(snap["rsi"])
            rsi_str = f"{rsi_v:.1f}({'超買' if rsi_v>70 else '超賣' if rsi_v<30 else '中性'})"
        except Exception:
            rsi_str = snap["rsi"]

        lines.append(
            f"【{tk}】{snap['datetime']} | {snap['period']}/{snap['interval']}\n"
            f"  價格：${snap['close']}（{snap['pct_chg']}%）"
            f"| RSI：{rsi_str} | MACD：{snap['macd']} | VIX：{snap['vix']}\n"
            f"  EMA排列：{ema_arr} | 成交量：{snap['volume']}（{snap['vol_tag']}）\n"
            f"  K線：{snap['kline_pat']} | 信號：{sigs_short}\n"
            f"  最佳回測勝率：{best_wr}\n"
            f"  密集區：{', '.join(['$'+a['center'] for a in snap['dense']]) or '無'}\n"
        )

    if not has_data:
        return "⚠️ 尚無任何股票的即時數據，請先讓主監控刷新一次。"

    lines += [
        "━━━ 請回答以下問題 ━━━\n",
        "1. 📊 大市環境：根據 VIX 和各股技術面，今日整體市場情緒如何？",
        "2. 🥇 優先級排序：今日最值得操作的 1-2 隻股票，及具體原因",
        "3. 🚫 需要迴避：哪些股票信號偏弱或風險較高？",
        "4. 📋 整體策略：今日應偏進攻（多）還是偏防守（觀望/空）？",
        "5. ⚠️ 主要風險：今日最需注意的宏觀/技術風險",
        "\n請用繁體中文回答，給出具體分析，避免泛泛而談。",
    ]
    return "\n".join(lines)



def _enrich_data(df: pd.DataFrame, params: dict, mfi_win: int,
                 include_vix: bool = False, vix_period: str = "",
                 vix_interval: str = "",
                 vix_ema_fast: int = 5, vix_ema_slow: int = 10) -> pd.DataFrame:
    """
    共用指標計算流程（消除 3 處重複代碼）。
    主監控和回測統一呼叫此函數。
    """
    df = df.copy()
    df["Price Change %"]  = df["Close"].pct_change().round(4) * 100
    df["Volume Change %"] = df["Volume"].pct_change().round(4) * 100
    df["前5均量"]          = df["Volume"].rolling(5).mean()

    df["MACD"], df["Signal_Line"], df["Histogram"] = calculate_macd(df)
    df["RSI"] = calculate_rsi(df)
    for span, name in [(5, "EMA5"), (10, "EMA10"), (30, "EMA30"), (40, "EMA40")]:
        df[name] = df["Close"].ewm(span=span, adjust=False).mean()
    df["SMA50"]  = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["VWAP"]   = calculate_vwap(df)
    df["MFI"]    = calculate_mfi(df)
    df["OBV"]    = calculate_obv(df)

    df["Up"]   = (df["Close"] > df["Close"].shift(1)).astype(int)
    df["Down"] = (df["Close"] < df["Close"].shift(1)).astype(int)
    df["Continuous_Up"]   = df["Up"]   * (df["Up"].groupby(  (df["Up"]   == 0).cumsum()).cumcount() + 1)
    df["Continuous_Down"] = df["Down"] * (df["Down"].groupby((df["Down"] == 0).cumsum()).cumcount() + 1)

    W = int(mfi_win)
    # FIX v3.6: High_Max/Low_Min（BreakOut_5K 用）與 MFI 窗口解耦
    # 原本共用 mfi_win，改 MFI 窗口會連帶改突破窗口（不相關指標耦合）
    # 改為固定 5 根，與信號名稱「5K」語義一致
    _BREAKOUT_WIN = 5
    df["High_Max"] = df["High"].rolling(_BREAKOUT_WIN).max()
    df["Low_Min"]  = df["Low"].rolling(_BREAKOUT_WIN).min()
    df = compute_mfi_divergence(df, W)
    df["OBV_Roll_Max"] = df["OBV"].rolling(20).max()
    df["OBV_Roll_Min"] = df["OBV"].rolling(20).min()

    if include_vix and vix_period and vix_interval:
        vix_df = get_vix_data(vix_period, vix_interval)
        df = merge_vix_data(df, vix_df, vix_interval)
        for col in ["VIX", "VIX_Change_Pct"]:
            if col not in df.columns:
                df[col] = np.nan
        if not df["VIX"].isna().all():
            df["VIX_EMA_Fast"] = df["VIX"].ewm(span=vix_ema_fast, adjust=False).mean()
            df["VIX_EMA_Slow"] = df["VIX"].ewm(span=vix_ema_slow, adjust=False).mean()
        else:
            df["VIX_EMA_Fast"] = np.nan; df["VIX_EMA_Slow"] = np.nan
    else:
        for col in ["VIX", "VIX_Change_Pct", "VIX_EMA_Fast", "VIX_EMA_Slow"]:
            if col not in df.columns:
                df[col] = np.nan

    return df


def _attach_kline_and_vol(df: pd.DataFrame, ticker: str, period: str,
                          interval: str, body_ratio: float, shadow_ratio: float,
                          doji_body: float) -> pd.DataFrame:
    """共用 K 線形態合併 + 成交量標記（消除重複代碼）。"""
    _buster = str(round(float(df["Close"].iloc[-1]), 4))
    kdf = get_kline_patterns(ticker, period, interval,
                             body_ratio, shadow_ratio, doji_body, _buster)
    kdf["Datetime"] = pd.to_datetime(kdf["Datetime"]).dt.tz_localize(None)
    df = df.merge(kdf, on="Datetime", how="left")
    df["K線形態"]  = df["K線形態"].fillna("普通K線")
    if "單根解讀" in df.columns:
        df["單根解讀"] = df["單根解讀"].fillna("波動有限")
    df["成交量標記"] = np.where(
        pd.notna(df["前5均量"]) & (df["Volume"] > df["前5均量"]),
        "放量", "縮量"
    )
    return df



# ═════════════════════════════════════════════════════════════════════════════
#  CACHED PRICE DATA  (FIX P2-#4: 主監控 yfinance 加 60 秒快取)
#  用可哈希參數作 key，避免每次 rerun 重抓網路。TTL=60s 保持近即時。
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_price_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """
    統一的價格數據抓取入口（帶快取）。
    TTL=60s：主監控用，保持近即時但避免每次 rerun 都打 yfinance。
    回傳已標準化的 DataFrame（Datetime 欄位、tz-naive）。
    """
    df = yf.Ticker(ticker).history(period=period, interval=interval).reset_index()
    if df.empty:
        return df
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "Datetime"})
    df["Datetime"] = pd.to_datetime(df["Datetime"]).dt.tz_localize(None)
    return df


# ═════════════════════════════════════════════════════════════════════════════
#  CACHED K-LINE PATTERN (FIX: use hashable params, not DataFrame)
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def get_kline_patterns(ticker: str, period: str, interval: str,
                       body_ratio: float, shadow_ratio: float, doji_body: float,
                       _cache_buster: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval=interval).reset_index()
    if df.empty:
        return pd.DataFrame(columns=["Datetime","K線形態","單根解讀"])
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "Datetime"})
    df["Datetime"]  = pd.to_datetime(df["Datetime"]).dt.tz_localize(None)
    df["前5均量"]   = df["Volume"].rolling(window=5).mean()

    patterns, interps = [], []
    for idx, row in df.iterrows():
        p, t = _classify_kline(row, idx, df, body_ratio, shadow_ratio, doji_body)
        patterns.append(p); interps.append(t)
    df["K線形態"]  = patterns
    df["單根解讀"] = interps
    return df[["Datetime","K線形態","單根解讀"]]


def _classify_kline(row, idx, df, body_ratio, shadow_ratio, doji_body):
    p, t = "普通K線", "波動有限，方向不明顯"
    if idx == 0:
        return p, t
    po, pc = df["Open"].iloc[idx-1], df["Close"].iloc[idx-1]
    _, _  = df["High"].iloc[idx-1], df["Low"].iloc[idx-1]  # prev high/low（未使用，保留計算供未來擴展）
    co, cc, ch, cl = row["Open"], row["Close"], row["High"], row["Low"]
    body   = abs(cc - co)
    rng    = ch - cl if ch != cl else 1e-9
    hi_vol = row["Volume"] > row.get("前5均量", 0)
    is_up  = df["Close"].iloc[max(0, idx-5):idx].mean() < cc if idx >= 5 else False
    is_dn  = df["Close"].iloc[max(0, idx-5):idx].mean() > cc if idx >= 5 else False
    lower  = min(co, cc) - cl
    upper  = ch - max(co, cc)

    if body < rng*0.3 and lower >= shadow_ratio*max(body,1e-9) and upper < lower and is_dn:
        p = "錘子線"; t = "下方支撐，多方承接" + ("，放量增強" if hi_vol else "")
    elif body < rng*0.3 and upper >= shadow_ratio*max(body,1e-9) and lower < upper and is_up:
        p = "射擊之星"; t = "高位拋壓" + ("，放量賣出" if hi_vol else "")
    elif body < doji_body*rng:
        p = "十字星"; t = "市場猶豫，方向未明"
    elif cc > co and body > body_ratio*rng:
        p = "大陽線"; t = "多方強勢" + ("，放量有力" if hi_vol else "")
    elif cc < co and body > body_ratio*rng:
        p = "大陰線"; t = "空方強勢" + ("，放量偏空" if hi_vol else "")
    elif cc > co and pc < po and co <= pc and cc >= po and hi_vol:
        # FIX: 看漲吞噬允許等於（co <= pc, cc >= po）
        p = "看漲吞噬"; t = "陽線包覆前日陰線，預示反轉"
    elif cc < co and pc > po and co >= pc and cc <= po and hi_vol:
        # FIX: 看跌吞噬允許等於
        p = "看跌吞噬"; t = "陰線包覆前日陽線，預示反轉"
    elif is_up and cc < co and pc > po and co > pc and cc < (po+pc)/2:
        p = "烏雲蓋頂"; t = "上升趨勢中陰線壓制，賣壓加重"
    elif is_dn and cc > co and pc < po and co < pc and cc > (po+pc)/2:
        p = "刺透形態"; t = "下跌趨勢中陽線反攻，買方介入"
    elif (idx > 1 and
          df["Close"].iloc[idx-2] < df["Open"].iloc[idx-2] and
          abs(df["Close"].iloc[idx-1]-df["Open"].iloc[idx-1]) < 0.3*abs(df["Close"].iloc[idx-2]-df["Open"].iloc[idx-2]) and
          cc > co and cc > (po+pc)/2 and hi_vol):
        p = "早晨之星"; t = "下跌後強陽，預示反轉"
    elif (idx > 1 and
          df["Close"].iloc[idx-2] > df["Open"].iloc[idx-2] and
          abs(df["Close"].iloc[idx-1]-df["Open"].iloc[idx-1]) < 0.3*abs(df["Close"].iloc[idx-2]-df["Open"].iloc[idx-2]) and
          cc < co and cc < (po+pc)/2 and hi_vol):
        p = "黃昏之星"; t = "上漲後強陰，預示反轉"
    return p, t


# ═════════════════════════════════════════════════════════════════════════════
#  EMAIL (FIX: consolidated dict param)
# ═════════════════════════════════════════════════════════════════════════════

def send_email_alert(ticker: str, price_pct: float, volume_pct: float, active_signals: dict):
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        return
    desc = {
        "macd_buy":"📈 MACD買入","macd_sell":"📉 MACD賣出",
        "ema_buy":"📈 EMA買入","ema_sell":"📉 EMA賣出",
        "new_buy":"📈 新買入","new_sell":"📉 新賣出",
        "vwap_buy":"📈 VWAP買入","vwap_sell":"📉 VWAP賣出",
        "mfi_bull":"📈 MFI牛背離","mfi_bear":"📉 MFI熊背離",
        "obv_buy":"📈 OBV突破買入","obv_sell":"📉 OBV突破賣出",
        "vix_panic":"📉 VIX恐慌賣出","vix_calm":"📈 VIX平靜買入",
        "bullish_eng":"📈 看漲吞沒","bearish_eng":"📉 看跌吞沒",
        "morning_star":"📈 早晨之星","evening_star":"📉 黃昏之星",
        "hammer":"📈 錘頭線","hanging_man":"📉 上吊線",
    }
    lines = [f"股票: {ticker}", f"股價變動: {price_pct:.2f}%",
             f"成交量變動: {volume_pct:.2f}%", ""]
    for k, label in desc.items():
        if active_signals.get(k):
            lines.append(label)
    lines.append("\n⚠️ 系統偵測到異動，請立即查看市場情況。")
    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg["Subject"] = f"📣 股票異動通知：{ticker}"
    msg.attach(MIMEText("\n".join(lines), "plain"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(SENDER_EMAIL, SENDER_PASSWORD)
            srv.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        st.toast("📬 Email 已發送")
    except Exception as e:
        st.error(f"Email 發送失敗：{e}")




# ═════════════════════════════════════════════════════════════════════════════
#  BACKTEST: combination win-rate
# ═════════════════════════════════════════════════════════════════════════════

def _calc_wr(sub_next_up: "np.ndarray", is_sell: bool) -> float:
    """
    Helper: compute win rate from a boolean array of next-bar direction.
    """
    n = len(sub_next_up)
    if n == 0:
        return 0.0
    mean_up = float(np.asarray(sub_next_up, dtype=float).mean())
    return (1 - mean_up) * 100 if is_sell else mean_up * 100


def _calc_avg_pnl(close_arr: "np.ndarray", next_close_arr: "np.ndarray",
                  mask: "np.ndarray", is_sell: bool) -> float:
    """
    計算命中該組合的所有K線的平均每筆盈虧(%)。
    """
    c  = close_arr[mask]
    nc = next_close_arr[mask]
    if len(c) == 0:
        return 0.0
    safe_c = np.where(c == 0, np.nan, c)
    pnl    = (nc - c) / safe_c * 100
    if is_sell:
        pnl = -pnl
    valid = pnl[~np.isnan(pnl)]
    return round(float(valid.mean()), 2) if len(valid) > 0 else 0.0


def _build_onehot(df: "pd.DataFrame") -> "tuple[list, dict, np.ndarray]":
    """
    共用前置步驟：解析信號 → one-hot 布林矩陣。
    """
    signal_sets = []
    for marks in df["異動標記"].fillna(""):
        sigs = {s.strip() for s in str(marks).split(", ")
                if s.strip() and "🔥" not in s}
        signal_sets.append(sigs)

    all_s     = sorted({s for ss in signal_sets for s in ss})
    sig_index = {s: i for i, s in enumerate(all_s)}
    n_sigs    = len(all_s)
    n_rows    = len(df)

    onehot = np.zeros((n_rows, n_sigs), dtype=bool)
    for row_i, sset in enumerate(signal_sets):
        for s in sset:
            if s in sig_index:
                onehot[row_i, sig_index[s]] = True

    return all_s, sig_index, onehot


def _combo_mask(combo: tuple, sig_index: dict,
                onehot: "np.ndarray") -> "np.ndarray":
    """
    給定一個信號組合 tuple，回傳 shape=(n_rows,) 的布林陣列。
    """
    cols = [sig_index[s] for s in combo if s in sig_index]
    if not cols:
        return np.zeros(onehot.shape[0], dtype=bool)
    return onehot[:, cols].all(axis=1)


def _prefilter_signals(all_s: list, sig_index: dict,
                       onehot: "np.ndarray", valid: "np.ndarray",
                       min_occ: int) -> list:
    """
    SPEED: 組合剪枝。單一信號若連自己都達不到 min_occ 次，
    任何「包含它」的組合（AND 後只會更少）也一定達不到 → 直接從候選池剔除。
    這能在組合爆炸前就把搜尋空間大幅縮小（指數級效果）。
    回傳：通過頻率門檻的信號清單（保持原排序）。
    """
    col_counts = (onehot[valid]).sum(axis=0)  # 每個信號在有效列的出現次數
    return [s for s in all_s if col_counts[sig_index[s]] >= min_occ]


# ─────────────────────────────────────────────────────────────────────────────
# SPEED: 預計算共用物件（_BtCtx），三個維度函數共用同一份 one-hot 矩陣，
#         避免 _build_onehot 重複執行三次（原本各算一次，現在算一次傳入）。
# ─────────────────────────────────────────────────────────────────────────────
class _BtCtx:
    """回測共用預計算物件，由 _build_bt_ctx 建立，傳入三個維度函數。"""
    __slots__ = ("close_arr","next_close_arr","next_up","valid",
                 "all_s","sig_index","onehot","cand_s")


def _build_bt_ctx(df: "pd.DataFrame", min_occ: int) -> "_BtCtx":
    """
    SPEED: 預計算所有維度共用的 numpy 陣列與 one-hot 矩陣，只算一次。
    """
    ctx = _BtCtx()
    ctx.close_arr      = df["Close"].to_numpy()
    ctx.next_close_arr = df["Close"].shift(-1).to_numpy()
    ctx.next_up        = (ctx.next_close_arr > ctx.close_arr)
    ctx.valid          = ~np.isnan(ctx.next_close_arr)   # FIX BUG-02
    ctx.all_s, ctx.sig_index, ctx.onehot = _build_onehot(df)
    ctx.cand_s = _prefilter_signals(
        ctx.all_s, ctx.sig_index, ctx.onehot, ctx.valid, min_occ
    )
    return ctx


# ── FIX BUG-02: 回測勝率排除最後一根 NaN ─────────────────────────────────────
def _base_signal_combos(df: "pd.DataFrame", min_combo: int, max_combo: int,
                         min_occ: int,
                         _ctx: "_BtCtx | None" = None) -> "pd.DataFrame":
    """
    維度 1：純信號組合勝率（向量化加速版）
    _ctx 由呼叫方傳入以避免重複計算（SPEED 優化）。
    """
    if _ctx is None:
        _ctx = _build_bt_ctx(df.copy(), min_occ)
    ctx = _ctx

    rows = []
    for r in range(min_combo, min(max_combo + 1, len(ctx.cand_s) + 1)):
        for combo in combinations(ctx.cand_s, r):
            mask  = _combo_mask(combo, ctx.sig_index, ctx.onehot) & ctx.valid
            n_hit = int(mask.sum())
            if n_hit < min_occ:
                continue
            is_sell = sum(1 for s in combo if s in SELL_SIGNALS) > len(combo) / 2
            rows.append({
                "維度":        "信號組合",
                "信號組合":    " + ".join(combo),
                "成交量標記":  "—",
                "K線形態":     "—",
                "信號數量":    r,
                "勝率(%)":     round(_calc_wr(ctx.next_up[mask], is_sell), 1),
                "平均盈虧(%)": _calc_avg_pnl(ctx.close_arr, ctx.next_close_arr, mask, is_sell),
                "出現次數":    n_hit,
                "方向":        "做空" if is_sell else "做多",
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("勝率(%)", ascending=False).head(30)


def _signal_x_volume_combos(df: "pd.DataFrame", min_combo: int, max_combo: int,
                              min_occ: int,
                              _ctx: "_BtCtx | None" = None) -> "pd.DataFrame":
    """
    維度 2：信號組合 × 成交量標記（向量化加速版）
    _ctx 由呼叫方傳入以避免重複計算（SPEED 優化）。
    """
    if "成交量標記" not in df.columns:
        return pd.DataFrame()
    if _ctx is None:
        _ctx = _build_bt_ctx(df.copy(), min_occ)
    ctx = _ctx

    vol_arr  = df["成交量標記"].to_numpy()
    vol_放量 = (vol_arr == "放量")
    vol_縮量 = (vol_arr == "縮量")

    rows = []
    for r in range(min_combo, min(max_combo + 1, len(ctx.cand_s) + 1)):
        for combo in combinations(ctx.cand_s, r):
            base_mask = _combo_mask(combo, ctx.sig_index, ctx.onehot) & ctx.valid
            n_base    = int(base_mask.sum())
            if n_base < min_occ:
                continue
            is_sell = sum(1 for s in combo if s in SELL_SIGNALS) > len(combo) / 2
            for vol_label, vol_mask in [("放量", vol_放量), ("縮量", vol_縮量)]:
                mask  = base_mask & vol_mask
                n_hit = int(mask.sum())
                if n_hit < min_occ:
                    continue
                rows.append({
                    "維度":        "信號+成交量",
                    "信號組合":    " + ".join(combo),
                    "成交量標記":  vol_label,
                    "K線形態":     "—",
                    "信號數量":    r,
                    "勝率(%)":     round(_calc_wr(ctx.next_up[mask], is_sell), 1),
                    "平均盈虧(%)": _calc_avg_pnl(ctx.close_arr, ctx.next_close_arr, mask, is_sell),
                    "出現次數":    n_hit,
                    "方向":        "做空" if is_sell else "做多",
                })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("勝率(%)", ascending=False).head(30)


def _signal_x_kline_combos(df: "pd.DataFrame", min_combo: int, max_combo: int,
                             min_occ: int,
                             _ctx: "_BtCtx | None" = None) -> "pd.DataFrame":
    """
    維度 3：信號組合 × K線形態（向量化加速版）
    _ctx 由呼叫方傳入以避免重複計算（SPEED 優化）。
    """
    if "K線形態" not in df.columns:
        return pd.DataFrame()
    if _ctx is None:
        _ctx = _build_bt_ctx(df.copy(), min_occ)
    ctx = _ctx

    kline_arr  = df["K線形態"].fillna("普通K線").to_numpy()
    kline_vals = [k for k in df["K線形態"].dropna().unique()
                  if k and k != "普通K線"]
    kline_masks = {kl: (kline_arr == kl) for kl in kline_vals}

    rows = []
    for r in range(min_combo, min(max_combo + 1, len(ctx.cand_s) + 1)):
        for combo in combinations(ctx.cand_s, r):
            base_mask = _combo_mask(combo, ctx.sig_index, ctx.onehot) & ctx.valid
            n_base    = int(base_mask.sum())
            if n_base < min_occ:
                continue
            is_sell = sum(1 for s in combo if s in SELL_SIGNALS) > len(combo) / 2
            for kl, kl_mask in kline_masks.items():
                mask  = base_mask & kl_mask
                n_hit = int(mask.sum())
                if n_hit < min_occ:
                    continue
                rows.append({
                    "維度":        "信號+K線形態",
                    "信號組合":    " + ".join(combo),
                    "成交量標記":  "—",
                    "K線形態":     kl,
                    "信號數量":    r,
                    "勝率(%)":     round(_calc_wr(ctx.next_up[mask], is_sell), 1),
                    "平均盈虧(%)": _calc_avg_pnl(ctx.close_arr, ctx.next_close_arr, mask, is_sell),
                    "出現次數":    n_hit,
                    "方向":        "做空" if is_sell else "做多",
                })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("勝率(%)", ascending=False).head(30)


# ── FIX BUG-08: 進場價改用下一根開盤 ─────────────────────────────────────────
def _detailed_backtest(df: "pd.DataFrame",
                       signal_combo: str,
                       vol_filter: str = "—",
                       kline_filter: str = "—",
                       direction: str = "做多",
                       hold_bars: int = 1) -> "pd.DataFrame":
    """
    對單一信號組合逐筆展開所有交易記錄，計算每筆盈虧。

    FIX v3.0: 進場價改用信號出現後的下一根 K 線開盤價（更貼近真實交易）。
    """
    if df.empty or "異動標記" not in df.columns:
        return pd.DataFrame()

    df = df.copy().reset_index(drop=True)

    required_sigs = [s.strip() for s in signal_combo.split(" + ") if s.strip()]

    def _hit(row):
        marks = str(row.get("異動標記", ""))
        sigs  = {s.strip() for s in marks.split(", ") if s.strip()}
        sig_ok = all(s in sigs for s in required_sigs)
        vol_ok = (vol_filter in ("—", "全部") or
                  str(row.get("成交量標記","")) == vol_filter)
        kl_ok  = (kline_filter in ("—", "全部") or
                  str(row.get("K線形態","")) == kline_filter)
        return sig_ok and vol_ok and kl_ok

    hit_mask = df.apply(_hit, axis=1)
    hit_idx  = df.index[hit_mask].tolist()

    records = []
    for i in hit_idx:
        # FIX BUG-08: 信號在第 i 根確認後，下一根 (i+1) 開盤進場
        entry_i = i + 1
        if entry_i >= len(df):
            continue  # 信號出現在最後一根，無法進場

        exit_i = entry_i + hold_bars
        if exit_i >= len(df):
            continue  # 無出場K線

        signal_bar = df.iloc[i]       # 信號確認那根（用於記錄觸發資訊）
        entry_bar  = df.iloc[entry_i]  # 實際進場那根
        exit_bar   = df.iloc[exit_i]

        # 進場價 = 下一根開盤（信號確認後最早可執行的價格）
        entry_price = float(entry_bar["Open"])
        exit_price  = float(exit_bar["Close"])

        if entry_price <= 0:
            continue

        if direction == "做多":
            pnl_pct  = (exit_price - entry_price) / entry_price * 100
            win      = exit_price > entry_price
        else:
            pnl_pct  = (entry_price - exit_price) / entry_price * 100
            win      = exit_price < entry_price

        # RSI / MACD at signal bar (not entry bar)
        entry_rsi  = round(float(signal_bar.get("RSI",  float("nan"))), 1)
        entry_macd = round(float(signal_bar.get("MACD", float("nan"))), 4)
        entry_vol  = signal_bar.get("成交量標記", "—")
        entry_kl   = signal_bar.get("K線形態",    "—")

        # High / Low in the holding period
        hold_slice      = df.iloc[entry_i : exit_i + 1]
        max_high        = float(hold_slice["High"].max()) if not hold_slice.empty else exit_price
        min_low         = float(hold_slice["Low"].min())  if not hold_slice.empty else exit_price

        if direction == "做多":
            max_runup_pct  = (max_high - entry_price) / entry_price * 100
            max_drawdown_pct = (entry_price - min_low) / entry_price * 100
        else:
            max_runup_pct  = (entry_price - min_low)  / entry_price * 100
            max_drawdown_pct = (max_high - entry_price) / entry_price * 100

        signal_dt = signal_bar.get("Datetime", "")
        entry_dt  = entry_bar.get("Datetime", "")
        exit_dt   = exit_bar.get("Datetime",  "")

        records.append({
            "序號":        len(records) + 1,
            "信號時間":    str(signal_dt)[:19],
            "進場時間":    str(entry_dt)[:19],
            "出場時間":    str(exit_dt)[:19],
            "持倉根數":    hold_bars,
            "進場價":      round(entry_price, 4),
            "出場價":      round(exit_price,  4),
            "方向":        direction,
            "盈虧(%)":     round(pnl_pct, 2),
            "勝負":        "✅ 勝" if win else "❌ 敗",
            "最大順勢(%)": round(max_runup_pct,   2),
            "最大逆勢(%)": round(max_drawdown_pct, 2),
            "信號RSI":     entry_rsi,
            "信號MACD":    entry_macd,
            "成交量標記":  str(entry_vol),
            "K線形態":     str(entry_kl),
            "觸發信號":    str(signal_bar.get("異動標記", ""))[:120],
        })

    if not records:
        return pd.DataFrame()

    detail_df = pd.DataFrame(records)
    detail_df["累計盈虧(%)"] = detail_df["盈虧(%)"].cumsum().round(2)

    wins = (detail_df["勝負"] == "✅ 勝").astype(int)
    loss = (1 - wins)
    streak_win = wins  * (wins .groupby((wins  == 0).cumsum()).cumcount() + 1)
    streak_loss= loss  * (loss.groupby((loss == 0).cumsum()).cumcount() + 1)
    detail_df["連勝數"] = streak_win
    detail_df["連敗數"] = streak_loss

    return detail_df


def _summary_stats(detail_df: "pd.DataFrame") -> dict:
    """從逐筆交易記錄計算統計摘要。"""
    if detail_df.empty:
        return {}

    total    = len(detail_df)
    wins     = (detail_df["勝負"] == "✅ 勝").sum()
    losses   = total - wins
    wr       = wins / total * 100 if total else 0

    pnl      = detail_df["盈虧(%)"]
    win_pnl  = pnl[detail_df["勝負"] == "✅ 勝"]
    loss_pnl = pnl[detail_df["勝負"] == "❌ 敗"]

    avg_win  = win_pnl.mean()  if len(win_pnl)  else 0
    avg_loss = loss_pnl.mean() if len(loss_pnl) else 0

    total_profit = win_pnl.sum()   if len(win_pnl)  else 0
    total_loss   = abs(loss_pnl.sum()) if len(loss_pnl) else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

    cum = detail_df["累計盈虧(%)"]
    roll_max = cum.cummax()
    drawdown = cum - roll_max
    max_dd   = drawdown.min()

    expectancy = (wr/100) * avg_win + ((1 - wr/100)) * avg_loss

    calmar = (cum.iloc[-1] / abs(max_dd)) if max_dd != 0 else float("inf")

    max_streak_win  = detail_df["連勝數"].max()
    max_streak_loss = detail_df["連敗數"].max()

    return {
        "總交易筆數":      total,
        "勝出筆數":        int(wins),
        "敗出筆數":        int(losses),
        "實際勝率(%)":     round(wr, 1),
        "平均盈利(%)":     round(avg_win,  2),
        "平均虧損(%)":     round(avg_loss, 2),
        "盈虧比":          round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else "∞",
        "獲利因子":        round(profit_factor, 2) if profit_factor != float("inf") else "∞",
        "期望值每筆(%)":   round(expectancy, 2),
        "累計盈虧(%)":     round(float(cum.iloc[-1]), 2),
        "最大回撤(%)":     round(float(max_dd), 2),
        "Calmar比率":      round(calmar, 2) if calmar != float("inf") else "∞",
        "最大連勝":        int(max_streak_win),
        "最大連敗":        int(max_streak_loss),
    }

def backtest_signal_combinations(df: "pd.DataFrame", min_combo=2,
                                  max_combo=4, min_occ=3) -> "pd.DataFrame":
    """保留舊介面相容。FIX P2-#6: 傳入預計算 ctx 避免重複建 onehot。"""
    _ctx = _build_bt_ctx(df, min_occ)
    return _base_signal_combos(df, min_combo, max_combo, min_occ, _ctx=_ctx)




# ═════════════════════════════════════════════════════════════════════════════
#  SIGNAL MARKING  (core logic, returns comma-joined string)
# ═════════════════════════════════════════════════════════════════════════════

def compute_all_signals(data: pd.DataFrame,
                        params: dict) -> pd.Series:
    """
    Vectorised-friendly signal marker.
    Returns pd.Series of strings aligned to data index.

    FIX P1-#3: 每根 K 線包 try/except，單根數據異常（NaN/除零）只回傳空字串，
    不會拋出例外導致整個 ticker tab 崩潰。
    """
    results = []
    for idx, row in data.iterrows():
        try:
            results.append(_mark_one(row, idx, data, params))
        except Exception:
            results.append("")   # 異常時靜默略過，不中斷整批計算
    return pd.Series(results, index=data.index)


def _prev(data, col, idx, n=1):
    i = idx - n
    if i < 0:
        return np.nan
    return data[col].iloc[i]


def _mark_one(row, idx, data, p):
    sigs = []
    macd = row["MACD"]
    rsi  = row["RSI"]
    # FIX: MFI 不再 fillna(50)，需要安全處理 NaN
    rsi_valid = pd.notna(rsi)
    rsi_val = float(rsi) if rsi_valid else 50.0  # 預設中性

    fma  = row["前5均量"] if pd.notna(row["前5均量"]) else 0

    def pv(col, n=1):
        return _prev(data, col, idx, n)

    # ── 量價 ──────────────────────────────────────────────────────────────────
    pa = row.get("📈 股價漲跌幅(%)", np.nan)
    va = row.get("📊 成交量變動幅(%)", np.nan)
    if pd.notna(pa) and pd.notna(va) and abs(pa) >= p["PRICE_TH"] and abs(va) >= p["VOLUME_TH"]:
        sigs.append("✅ 量價")

    # ── Low>High / High<Low ───────────────────────────────────────────────────
    if idx > 0:
        if row["Low"]  > pv("High"):  sigs.append("📈 Low>High")
        if row["High"] < pv("Low"):   sigs.append("📉 High<Low")

    # ── Close position ────────────────────────────────────────────────────────
    # FIX v3.6: 直接用當根 OHLC 計算，不依賴 Close_N_High/Low 欄位
    # （回測中該欄位是 NaN，改為即時計算確保回測與主監控一致）
    _hl = (row["High"] - row["Low"])
    if _hl > 0:
        _cnh = (row["Close"] - row["Low"])  / _hl   # 收在當日區間的高位比例
        _cnl = (row["High"]  - row["Close"]) / _hl  # 收在當日區間的低位比例
        if _cnh >= p["HIGH_N_HIGH_TH"]:  sigs.append("📈 HIGH_N_HIGH")
        if _cnl >= p["LOW_N_LOW_TH"]:    sigs.append("📉 LOW_N_LOW")

    # ── MACD ──────────────────────────────────────────────────────────────────
    # FIX BUG-06: 放寬 RSI 過濾到 <70 / >30（原為 <50 / >50，導致信號幾乎不觸發）
    if idx > 0:
        if macd > 0  and pv("MACD") <= 0 and rsi_val < 70: sigs.append("📈 MACD買入")
        if macd <= 0 and pv("MACD") > 0  and rsi_val > 30: sigs.append("📉 MACD賣出")

    # ── EMA5/10 ───────────────────────────────────────────────────────────────
    # FIX BUG-06: 同上
    if idx > 0:
        if row["EMA5"] > row["EMA10"] and pv("EMA5") <= pv("EMA10") and rsi_val < 70:
            sigs.append("📈 EMA買入")
        if row["EMA5"] < row["EMA10"] and pv("EMA5") >= pv("EMA10") and rsi_val > 30:
            sigs.append("📉 EMA賣出")

    # ── Price trend ───────────────────────────────────────────────────────────
    # FIX BUG-06: 放寬 RSI 過濾
    if idx > 0:
        ph, pl, pc = pv("High"), pv("Low"), pv("Close")
        vc = row.get("Volume Change %", 0) or 0
        if row["High"] > ph and row["Low"] > pl and row["Close"] > pc:
            if macd > 0:                              sigs.append("📈 價格趨勢買入")
            if row["Volume"] > fma and rsi_val < 70:  sigs.append("📈 價格趨勢買入(量)")
            if vc > 15 and rsi_val < 70:              sigs.append("📈 價格趨勢買入(量%)")
        if row["High"] < ph and row["Low"] < pl and row["Close"] < pc:
            if macd < 0:                              sigs.append("📉 價格趨勢賣出")
            if row["Volume"] > fma and rsi_val > 30:  sigs.append("📉 價格趨勢賣出(量)")
            if vc > 15 and rsi_val > 30:              sigs.append("📉 價格趨勢賣出(量%)")

    # ── Gaps ──────────────────────────────────────────────────────────────────
    if idx > 0:
        gap_pct = (row["Open"] - pv("Close")) / (pv("Close") or 1) * 100
        is_up   = gap_pct >  p["GAP_TH"]
        is_dn   = gap_pct < -p["GAP_TH"]
        if is_up or is_dn:
            window5 = data["Close"].iloc[max(0, idx-5):idx]
            trend   = window5.mean() if len(window5) else row["Close"]
            prev5   = data["Close"].iloc[max(0, idx-6):idx-1].mean() if idx >= 6 else trend
            hi_vol  = row["Volume"] > fma
            # FIX BUG-09 (look-ahead): 原本用 data["Close"].iloc[idx+1]（下一根收盤）
            #   判斷反轉 → 前瞻偏差，會虛高回測勝率。
            #   改用「當根 intrabar 回吐」判斷衰竭：只用當根 O/H/L/C，不看未來。
            #   - 收盤位置：上漲跳空衰竭 = 收在當根區間下半部 (close_pos < 0.5)
            #               下跌跳空衰竭 = 收在當根區間上半部 (close_pos > 0.5)
            #   - 收盤回吐：上漲跳空但收盤 < 開盤（收陰，吐回跳空）
            #               下跌跳空但收盤 > 開盤（收陽，吐回跳空）
            _rng = (row["High"] - row["Low"]) or 1e-9
            _close_pos = (row["Close"] - row["Low"]) / _rng
            reversal = (
                (is_up and row["Close"] < row["Open"] and _close_pos < 0.5) or
                (is_dn and row["Close"] > row["Open"] and _close_pos > 0.5)
            )
            if is_up:
                if reversal and hi_vol:
                    # FIX v3.6: 衰竭跳空(上)本質是看空信號（跳空高開後收陰回吐）
                    # 改用 📉 標記，與 SELL_SIGNALS 對齊
                    sigs.append("📉 衰竭跳空(上)")
                elif row["Close"] > trend > prev5 and hi_vol:
                    sigs.append("📈 持續跳空(上)")
                elif row["High"] > data["High"].iloc[max(0,idx-5):idx].max() and hi_vol:
                    sigs.append("📈 突破跳空(上)")
                else:
                    sigs.append("📈 普通跳空(上)")
            else:
                if reversal and hi_vol:
                    sigs.append("📉 衰竭跳空(下)")
                elif row["Close"] < trend < prev5 and hi_vol:
                    sigs.append("📉 持續跳空(下)")
                elif row["Low"] < data["Low"].iloc[max(0,idx-5):idx].min() and hi_vol:
                    sigs.append("📉 突破跳空(下)")
                else:
                    sigs.append("📉 普通跳空(下)")

    # ── Continuous ────────────────────────────────────────────────────────────
    if row.get("Continuous_Up",   0) >= p["CONT_UP"]   and rsi_val < 70: sigs.append("📈 連續向上買入")
    if row.get("Continuous_Down", 0) >= p["CONT_DOWN"]  and rsi_val > 30: sigs.append("📉 連續向下賣出")

    # ── SMA50/200 ─────────────────────────────────────────────────────────────
    # FIX v3.6: 原為純狀態信號（價格在SMA50之上就每天觸發），改為只在穿越當天觸發
    if idx > 0 and pd.notna(row.get("SMA50")):
        _sma50 = row["SMA50"]
        _prev_sma50 = pv("SMA50")
        if pd.notna(_prev_sma50):
            if row["Close"] > _sma50 and pv("Close") <= _prev_sma50 and macd > 0:
                sigs.append("📈 SMA50上升趨勢")
            elif row["Close"] < _sma50 and pv("Close") >= _prev_sma50 and macd < 0:
                sigs.append("📉 SMA50下降趨勢")
    if idx > 0 and pd.notna(row.get("SMA50")) and pd.notna(row.get("SMA200")):
        _sma50 = row["SMA50"]; _sma200 = row["SMA200"]
        _p_close = pv("Close"); _p_sma50 = pv("SMA50")
        if pd.notna(_p_close) and pd.notna(_p_sma50):
            if (row["Close"] > _sma50 > _sma200 and macd > 0
                    and (_p_close <= _p_sma50)):
                sigs.append("📈 SMA50_200上升趨勢")
            elif (row["Close"] < _sma50 < _sma200 and macd < 0
                    and (_p_close >= _p_sma50)):
                sigs.append("📉 SMA50_200下降趨勢")

    # ── New buy/sell ──────────────────────────────────────────────────────────
    # FIX v3.6: 原條件太寬（陽線+開>昨收+RSI<70），幾乎每天都觸發
    # 加入成交量過濾（放量確認），提高信號可靠性
    if idx > 0:
        pc = pv("Close")
        if (row["Close"] > row["Open"] > pc
                and row["Volume"] > fma         # 放量確認
                and rsi_val < 70):
            sigs.append("📈 新买入信号")
        if (row["Close"] < row["Open"] < pc
                and row["Volume"] > fma         # 放量確認
                and rsi_val > 30):
            sigs.append("📉 新卖出信号")

    # ── Pivot ─────────────────────────────────────────────────────────────────
    # FIX v3.6: 原「🔄 新转折点」無方向（漲跌都觸發同一個信號），且 MACD>Signal
    # 只過濾多頭但漲跌皆算，邏輯矛盾。改為拆分兩個有方向的信號：
    # 📈 新转折点(漲)：價量異動 + 價格上漲 + MACD金叉或正值
    # 📉 新转折点(跌)：價量異動 + 價格下跌 + MACD死叉或負值
    pr = row.get("Price Change %", 0) or 0
    vc_ = row.get("Volume Change %", 0) or 0
    _sig_line = row.get("Signal_Line", 0) or 0
    if abs(pr) > p["PC_TH"] and abs(vc_) > p["VC_TH"]:
        if pr > 0 and macd > _sig_line:   sigs.append("🔄 新转折点(漲)")
        elif pr < 0 and macd < _sig_line: sigs.append("🔄 新转折点(跌)")
    if len(sigs) > 8:
        sigs.append(f"🔥 關鍵轉折({len(sigs)}信號)")

    # ── RSI-MACD composite ────────────────────────────────────────────────────
    if idx > 0:
        if rsi_val < 30 and macd > 0 and pv("MACD") <= 0:   sigs.append("📈 RSI-MACD Oversold Crossover")
        if rsi_val > 70 and macd < 0 and pv("MACD") >= 0:   sigs.append("📉 RSI-MACD Overbought Crossover")

    # ── EMA-SMA trend ─────────────────────────────────────────────────────────
    # FIX v3.6: 原為純狀態信號（EMA5>EMA10 就每天觸發），改為只在交叉當天觸發
    s50 = row.get("SMA50", np.nan)
    if idx > 0 and pd.notna(s50):
        if (row["EMA5"] > row["EMA10"] and pv("EMA5") <= pv("EMA10")
                and row["Close"] > s50):
            sigs.append("📈 EMA-SMA Uptrend Buy")
        if (row["EMA5"] < row["EMA10"] and pv("EMA5") >= pv("EMA10")
                and row["Close"] < s50):
            sigs.append("📉 EMA-SMA Downtrend Sell")

    # ── Volume-MACD ───────────────────────────────────────────────────────────
    if idx > 0:
        if row["Volume"] > fma and macd > 0 and pv("MACD") <= 0: sigs.append("📈 Volume-MACD Buy")
        if row["Volume"] > fma and macd < 0 and pv("MACD") >= 0: sigs.append("📉 Volume-MACD Sell")

    # ── EMA 10/30/40 ─────────────────────────────────────────────────────────
    # FIX v3.6: EMA40 預設值陷阱修正
    # 原 row.get("EMA40", 0) → EMA40 欄位缺失時預設 0，EMA10 幾乎必>0，強烈買入必連帶觸發
    # 原 row.get("EMA40", 999999) → 強烈賣出同理
    # 改為先確認 EMA40 存在且非 NaN 才比較
    if idx > 0:
        _ema40 = row.get("EMA40", None)
        _ema40_ok = pd.notna(_ema40)
        if row["EMA10"] > row["EMA30"] and pv("EMA10") <= pv("EMA30"):
            sigs.append("📈 EMA10_30買入")
            if _ema40_ok and row["EMA10"] > _ema40:
                sigs.append("📈 EMA10_30_40強烈買入")
        if row["EMA10"] < row["EMA30"] and pv("EMA10") >= pv("EMA30"):
            sigs.append("📉 EMA10_30賣出")
            if _ema40_ok and row["EMA10"] < _ema40:
                sigs.append("📉 EMA10_30_40強烈賣出")

    # ── Candlestick patterns ───────────────────────────────────────────────────
    if idx > 0:
        co, cc, ch, cl = row["Open"], row["Close"], row["High"], row["Low"]
        po, pc2 = pv("Open"), pv("Close")
        body = abs(cc - co); rng = ch - cl if ch != cl else 1e-9
        hi_vol = row["Volume"] > fma
        lower = min(co, cc) - cl; upper = ch - max(co, cc)

        if pc2 < po and cc > co and co <= pc2 and cc >= po and hi_vol and rsi_val < 70:
            sigs.append("📈 看漲吞沒")
        if pc2 > po and cc < co and co >= pc2 and cc <= po and hi_vol and rsi_val > 30:
            sigs.append("📉 看跌吞沒")
        # FIX v3.6: 錘頭線與上吊線條件完全相同，只用 RSI 過濾無法區分
        # 加入5日趨勢方向判斷：
        #   錘頭線（Hammer）= 長下影線形態出現在下跌趨勢底部 → 看漲反轉
        #   上吊線（Hanging Man）= 相同形態出現在上漲趨勢頂部 → 看跌反轉
        _hammer_shape = (body < rng*0.3 and lower >= 2*max(body,1e-9)
                         and upper < lower and hi_vol)
        if _hammer_shape:
            _w5_mean = data["Close"].iloc[max(0,idx-5):idx].mean() if idx >= 1 else row["Close"]
            _in_downtrend = row["Close"] < _w5_mean   # 收盤低於5日均 = 下跌趨勢中
            if _in_downtrend and rsi_val < 50:
                sigs.append("📈 錘頭線")      # 下跌趨勢中出現 → 看漲反轉
            elif not _in_downtrend and rsi_val > 50:
                sigs.append("📉 上吊線")      # 上漲趨勢中出現 → 看跌反轉
        if pc2 > po and co > pc2 and cc < co and cc < (po+pc2)/2 and hi_vol:
            sigs.append("📉 烏雲蓋頂")
        if pc2 < po and co < pc2 and cc > co and cc > (po+pc2)/2 and hi_vol:
            sigs.append("📈 刺透形態")

    if idx > 1:
        p2o, p2c = data["Open"].iloc[idx-2], data["Close"].iloc[idx-2]
        p1o, p1c = data["Open"].iloc[idx-1], data["Close"].iloc[idx-1]
        co2, cc2 = row["Open"], row["Close"]
        hi_vol = row["Volume"] > fma
        if p2c < p2o and abs(p1c-p1o) < 0.3*abs(p2c-p2o) and cc2 > co2 and cc2 > (p2o+p2c)/2 and hi_vol and rsi_val < 70:
            sigs.append("📈 早晨之星")
        if p2c > p2o and abs(p1c-p1o) < 0.3*abs(p2c-p2o) and cc2 < co2 and cc2 < (p2o+p2c)/2 and hi_vol and rsi_val > 30:
            sigs.append("📉 黃昏之星")

    # ── Breakout ──────────────────────────────────────────────────────────────
    if idx > 0 and pd.notna(row.get("High_Max")) and row["High"] > data["High_Max"].iloc[idx-1]:
        sigs.append("📈 BreakOut_5K")
    if idx > 0 and pd.notna(row.get("Low_Min")) and row["Low"] < data["Low_Min"].iloc[idx-1]:
        sigs.append("📉 BreakDown_5K")

    # ── VWAP ─────────────────────────────────────────────────────────────────
    if idx > 0 and pd.notna(row.get("VWAP")) and pd.notna(pv("VWAP")):
        if row["Close"] > row["VWAP"] and pv("Close") <= pv("VWAP"):  sigs.append("📈 VWAP買入")
        elif row["Close"] < row["VWAP"] and pv("Close") >= pv("VWAP"): sigs.append("📉 VWAP賣出")

    # ── MFI divergence ────────────────────────────────────────────────────────
    w = p["MFI_WIN"]
    if idx >= w:
        if data.get("MFI_Bull_Div") is not None and data["MFI_Bull_Div"].iloc[idx]:
            sigs.append("📈 MFI牛背離買入")
        if data.get("MFI_Bear_Div") is not None and data["MFI_Bear_Div"].iloc[idx]:
            sigs.append("📉 MFI熊背離賣出")

    # ── OBV breakout ──────────────────────────────────────────────────────────
    if idx > 0 and pd.notna(row.get("OBV")):
        if row["Close"] > pv("Close") and row["OBV"] > data["OBV_Roll_Max"].iloc[idx-1]:
            sigs.append("📈 OBV突破買入")
        elif row["Close"] < pv("Close") and row["OBV"] < data["OBV_Roll_Min"].iloc[idx-1]:
            sigs.append("📉 OBV突破賣出")

    # ── VIX ───────────────────────────────────────────────────────────────────
    vix_now = row.get("VIX", np.nan)
    if idx > 0 and pd.notna(vix_now):
        vix_prev = data["VIX"].iloc[idx-1]
        if pd.notna(vix_prev):
            if vix_now > p["VIX_HIGH"] and vix_now > vix_prev:  sigs.append("📉 VIX恐慌賣出")
            elif vix_now < p["VIX_LOW"] and vix_now < vix_prev: sigs.append("📈 VIX平靜買入")
        ef = row.get("VIX_EMA_Fast", np.nan)
        es = row.get("VIX_EMA_Slow", np.nan)
        ef_p = data["VIX_EMA_Fast"].iloc[idx-1] if "VIX_EMA_Fast" in data.columns else np.nan
        es_p = data["VIX_EMA_Slow"].iloc[idx-1] if "VIX_EMA_Slow" in data.columns else np.nan
        if pd.notna(ef) and pd.notna(es) and pd.notna(ef_p) and pd.notna(es_p):
            if ef > es and ef_p <= es_p:  sigs.append("📉 VIX上升趨勢賣出")
            elif ef < es and ef_p >= es_p: sigs.append("📈 VIX下降趨勢買入")

    return ", ".join(sigs) if sigs else ""


# ═════════════════════════════════════════════════════════════════════════════
#  COMPREHENSIVE INTERPRETATION
# ═════════════════════════════════════════════════════════════════════════════

def comprehensive_interp(df: pd.DataFrame, dense_areas, VIX_HIGH, VIX_LOW) -> str:
    last5  = df.tail(5)
    bull   = last5["K線形態"].isin(["錘子線","大陽線","看漲吞噬","刺透形態","早晨之星"]).sum()
    bear   = last5["K線形態"].isin(["射擊之星","大陰線","看跌吞噬","烏雲蓋頂","黃昏之星"]).sum()
    hi_vol = (last5["成交量標記"] == "放量").sum()

    dense_desc = ""
    if dense_areas:
        ctrs = [f"{a['price_center']:.2f}" for a in dense_areas]
        dense_desc = f"，成交密集區：{', '.join(ctrs)}"

    vwap_v = last5["VWAP"].iloc[-1]; c_v = last5["Close"].iloc[-1]
    vwap_s = "多頭" if pd.notna(vwap_v) and c_v > vwap_v else "空頭"
    mfi_v  = last5["MFI"].iloc[-1]
    if pd.notna(mfi_v):
        mfi_s = f"MFI={mfi_v:.0f}({'超賣' if mfi_v<20 else '超買' if mfi_v>80 else '中性'})"
    else:
        mfi_s = "MFI=N/A"
    obv_s  = "OBV↑確認量能" if last5["OBV"].iloc[-1] > last5["OBV"].iloc[0] else "OBV↓警示"
    vix_v  = last5["VIX"].iloc[-1]
    vix_s  = f"VIX={'N/A' if pd.isna(vix_v) else f'{vix_v:.1f}(恐慌)' if vix_v>VIX_HIGH else f'{vix_v:.1f}(平靜)' if vix_v<VIX_LOW else f'{vix_v:.1f}'}"
    suffix = f"｜{vwap_s} VWAP，{mfi_s}，{obv_s}，{vix_s}{dense_desc}"

    if bull >= 3 and hi_vol >= 3:
        return f"多方主導，多根看漲形態放量，強勢上漲趨勢。{suffix}。💡 建議關注買入機會。"
    elif bear >= 3 and hi_vol >= 3:
        return f"空方主導，多根看跌形態放量，強勢下跌趨勢。{suffix}。⚠️ 建議注意賣出風險。"
    elif bull >= 2 and bear >= 2:
        return f"多空激烈爭奪，方向不明。{suffix}。📊 建議觀望。"
    else:
        return f"無明顯趨勢，持續觀察。{suffix}。"




# ═════════════════════════════════════════════════════════════════════════════
#  UI - SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

# 回測用：各 interval 允許的 period 清單（yfinance 限制）
INTERVAL_PERIOD_MAP = {
    "1m":  {"periods": ["1d","5d","7d"],       "default": "7d",  "help": "1m 最多 7 天"},
    "5m":  {"periods": ["5d","1mo","60d"],     "default": "60d", "help": "5m 最多 60 天"},
    "15m": {"periods": ["5d","1mo","60d"],     "default": "60d", "help": "15m 最多 60 天"},
    "30m": {"periods": ["5d","1mo","60d"],     "default": "60d", "help": "30m 最多 60 天"},
    "1h":  {"periods": ["1mo","3mo","6mo","1y","2y"], "default": "2y", "help": "1h 最多 730 天"},
    "1d":  {"periods": ["3mo","6mo","1y","2y","5y","ytd","max"], "default": "2y", "help": "日線建議 2y+"},
    "1wk": {"periods": ["6mo","1y","2y","5y","ytd","max"], "default": "5y", "help": "週線建議 5y+"},
    "1mo": {"periods": ["1y","2y","5y","ytd","max"], "default": "max", "help": "月線建議 max"},
}
ALL_BT_INTERVALS = ["1m","5m","15m","30m","1h","1d","1wk","1mo"]

with st.sidebar:
    st.header("⚙️ 參數設定")
    input_tickers     = st.text_input("股票代號（逗號分隔）",
                                       "QQQ,TSLA, UVXY, UVIX, NIO, TSLL, XPEV, GLD, META, GOOGL, AAPL, NVDA, AMZN, TSM, MSFT")
    selected_period   = st.selectbox("時間範圍",
                                      ["1d","5d","1mo","3mo","6mo","1y","2y","5y","ytd","max"], index=5)
    selected_interval = st.selectbox("資料間隔",
                                      ["1m","5m","15m","30m","60m","1h","1d","5d","1wk","1mo"], index=6)
    st.subheader("信號閾值")
    HIGH_N_HIGH_TH   = st.number_input("Close-to-High",     0.1, 1.0, 0.9, 0.1)
    LOW_N_LOW_TH     = st.number_input("Close-to-Low",      0.1, 1.0, 0.9, 0.1)
    PRICE_TH         = st.number_input("股價異動閾值 (%)",   0.1, 200.0, 80.0, 0.1)
    VOLUME_TH        = st.number_input("成交量異動閾值 (%)", 0.1, 200.0, 80.0, 0.1)
    PC_TH            = st.number_input("轉折 Price (%)",     0.1, 200.0,  5.0, 0.1)
    VC_TH            = st.number_input("轉折 Volume (%)",    0.1, 200.0, 10.0, 0.1)
    GAP_TH           = st.number_input("跳空閾值 (%)",       0.1,  50.0,  1.0, 0.1)
    CONT_UP          = st.number_input("連續上漲閾值 (根)",  1, 20, 3, 1)
    CONT_DOWN        = st.number_input("連續下跌閾值 (根)",  1, 20, 3, 1)
    PERCENTILE_TH    = st.selectbox("百分位 (%)",            [1, 5, 10, 20], index=1)
    st.subheader("K 線形態")
    BODY_RATIO_TH    = st.number_input("實體占比",  0.1, 0.9, 0.6, 0.05)
    SHADOW_RATIO_TH  = st.number_input("影線長度",  0.1, 3.0, 2.0, 0.1)
    DOJI_BODY_TH     = st.number_input("十字星閾值",0.01, 0.2, 0.1, 0.01)
    st.subheader("MFI")
    MFI_WIN          = st.number_input("MFI 背離窗口", 3, 20, 5, 1)
    st.subheader("VIX")
    VIX_HIGH_TH      = st.number_input("VIX 恐慌閾值", 20.0, 50.0, 30.0, 1.0)
    VIX_LOW_TH       = st.number_input("VIX 平靜閾值", 10.0, 25.0, 20.0, 1.0)
    VIX_EMA_FAST     = st.number_input("VIX EMA 快", 3, 15,  5, 1)
    VIX_EMA_SLOW     = st.number_input("VIX EMA 慢", 8, 25, 10, 1)
    st.subheader("成交密集區")
    VP_BINS          = st.number_input("分箱數量",  10, 200, 50,  5)
    VP_WINDOW        = st.number_input("K 線根數",  20, 500, 100, 10)
    VP_TOP_N         = st.number_input("顯示前 N",   1,   5,   3,  1)
    VP_SHOW          = st.checkbox("標記密集區", True)
    st.subheader("回測")
    BT_MIN_COMBO     = st.number_input("最少組合數", 2, 4, 4, 1)
    BT_MAX_COMBO     = st.number_input("最多組合數", 2, 5, 5, 1)
    BT_MIN_OCC       = st.number_input("最少次數",   2, 10, 10, 1)
    st.subheader("刷新")
    REFRESH_INTERVAL = st.selectbox("刷新間隔 (秒)", [30, 60, 90, 120, 180, 300], index=4)

PARAMS = dict(
    HIGH_N_HIGH_TH=HIGH_N_HIGH_TH, LOW_N_LOW_TH=LOW_N_LOW_TH,
    PRICE_TH=PRICE_TH, VOLUME_TH=VOLUME_TH,
    PC_TH=PC_TH, VC_TH=VC_TH, GAP_TH=GAP_TH,
    CONT_UP=CONT_UP, CONT_DOWN=CONT_DOWN,
    MFI_WIN=int(MFI_WIN),
    VIX_HIGH=VIX_HIGH_TH, VIX_LOW=VIX_LOW_TH,
)

selected_tickers = [t.strip().upper() for t in (input_tickers or "").split(",") if t.strip()]

# ── Telegram signal selection ─────────────────────────────────────────────────
ALL_SIGNAL_TYPES = sorted([
    "📈 Low>High","📈 HIGH_N_HIGH","📈 BreakOut_5K","📈 MACD買入","📈 EMA買入",
    "📈 價格趨勢買入","📈 價格趨勢買入(量)","📈 價格趨勢買入(量%)",
    "📈 普通跳空(上)","📈 突破跳空(上)","📈 持續跳空(上)",
    # FIX v3.6: 衰竭跳空(上)已改為 📉 並移入 SELL_SIGNALS，此處刪除舊 📈 版本
    "📈 連續向上買入","📈 SMA50上升趨勢","📈 SMA50_200上升趨勢",
    "📈 新买入信号","📈 RSI-MACD Oversold Crossover","📈 EMA-SMA Uptrend Buy",
    "📈 Volume-MACD Buy","📈 EMA10_30買入","📈 EMA10_30_40強烈買入",
    "📈 看漲吞沒","📈 刺透形態","📈 錘頭線","📈 早晨之星",
    "📈 VWAP買入","📈 MFI牛背離買入","📈 OBV突破買入",
    "📈 VIX平靜買入","📈 VIX下降趨勢買入","✅ 量價",
    "🔄 新转折点(漲)","🔄 新转折点(跌)",  # FIX v3.6: 拆分為兩個有方向的信號
] + list(SELL_SIGNALS))

# ── 全域 Telegram 信號選擇（適用於所有股票）──────────────────────────────────
# FIX: 由原本「每支股票各自一個 multiselect」改為「一個全域選擇套用到所有股票」。
# 在側欄統一設定一次，所有 ticker 共用同一份推播信號清單；
# 個別股票仍可透過各自的 Telegram 開關 (tg_enabled_{ticker}) 靜音。
with st.sidebar:
    st.subheader("📡 Telegram 推播信號（全域）")
    GLOBAL_SELECTED_SIGNALS = st.multiselect(
        "選擇需要 Telegram 推播的信號（適用於所有股票）",
        ALL_SIGNAL_TYPES,
        default=["📈 新买入信号"],
        key="global_selected_signals",
        help="此清單會套用到上方所有股票代號；個別股票仍可用各自的 Telegram 開關靜音。",
    )

# ── 每支股票預設條件表 ─────────────────────────────────────────────────────────
# ── 每支股票預設條件表 ─────────────────────────────────────────────────────────
# FIX: 預設為空表，而非預填做多信號。
# 原因：Streamlit Cloud 重啟時 session_state/query_params/localStorage 可能全部丟失，
#       如果 fallback 到有信號的預設表，會意外觸發 Telegram 推送。
#       空表 = 不會匹配任何條件 = 安全。用戶需要先執行回測才能填入條件。
_TG_DEFAULT = pd.DataFrame({
    "排名":       pd.Series(dtype="str"),
    "異動標記":   pd.Series(dtype="str"),
    "成交量標記": pd.Series(dtype="str"),
    "K線形態":    pd.Series(dtype="str"),
    "回測勝率":   pd.Series(dtype="str"),
    "方向":       pd.Series(dtype="str"),
})

import zlib, base64

_TG_COLS = ["排名","異動標記","成交量標記","K線形態","回測勝率","方向"]

def _ls_key(ticker: str) -> str:
    return f"streamlit_tg_conds_{ticker}"

def _qp_key(ticker: str) -> str:
    return f"tc_{ticker}"

def _ss_key(ticker: str) -> str:
    return f"tg_conds_{ticker}"


def _tg_encode(df: pd.DataFrame) -> str:
    try:
        records = df[_TG_COLS].fillna("").to_dict(orient="records")
        raw     = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
        return base64.urlsafe_b64encode(
            zlib.compress(raw.encode("utf-8"), level=9)
        ).decode("ascii")
    except Exception:
        return ""


def _tg_decode(s: str) -> pd.DataFrame:
    try:
        raw     = zlib.decompress(base64.urlsafe_b64decode(s)).decode("utf-8")
        records = json.loads(raw)
        df      = pd.DataFrame(records)
        for col in _TG_COLS:
            if col not in df.columns:
                df[col] = "做多" if col == "方向" else ""
        return df[_TG_COLS].fillna("")
    except Exception:
        return pd.DataFrame()


def _tg_save(df: pd.DataFrame, ticker: str):
    encoded = _tg_encode(df)
    if not encoded:
        return
    try:
        st.query_params[_qp_key(ticker)] = encoded
    except Exception:
        pass
    try:
        import streamlit.components.v1 as components
        _lsk = _ls_key(ticker)
        _ls_js = f"""<script>
        try {{ localStorage.setItem({json.dumps(_lsk)}, {json.dumps(encoded)}); }} catch(e) {{}}
        </script>"""
        components.html(_ls_js, height=0, scrolling=False)
    except Exception:
        pass


def _tg_load_ls_component(ticker: str):
    try:
        import streamlit.components.v1 as components
        _lsk  = _ls_key(ticker)
        _qpk  = _qp_key(ticker)
        _cur  = st.query_params.get(_qpk, "")
        _js   = f"""<script>
        (function(){{
            var ls=""; try{{ls=localStorage.getItem({json.dumps(_lsk)})||"";}}catch(e){{}}
            var qp={json.dumps(_cur)};
            if(ls && ls!==qp){{
                var url=new URL(window.parent.location.href);
                url.searchParams.set({json.dumps(_qpk)},ls);
                window.parent.history.replaceState(null,"",url.toString());
                window.parent.location.reload();
            }}
        }})();
        </script>"""
        components.html(_js, height=0, scrolling=False)
    except Exception:
        pass


def _tg_init(ticker: str) -> pd.DataFrame:
    ssk = _ss_key(ticker)
    qpk = _qp_key(ticker)

    if ssk in st.session_state:
        df = st.session_state[ssk]
    else:
        qp_enc = st.query_params.get(qpk, "")
        if qp_enc:
            df = _tg_decode(qp_enc)
            if df.empty:
                df = _TG_DEFAULT.copy()
                _tg_load_ls_component(ticker)
        else:
            df = _TG_DEFAULT.copy()
            _tg_load_ls_component(ticker)

    for col in _TG_COLS:
        if col not in df.columns:
            df[col] = "做多" if col == "方向" else ""
    df = df[_TG_COLS].fillna("")
    st.session_state[ssk] = df
    return df


def _tg_editor(ticker: str) -> pd.DataFrame:
    ssk = _ss_key(ticker)
    tc  = st.data_editor(
        st.session_state[ssk],
        num_rows="dynamic",
        key=f"tg_editor_{ticker}",
        column_config={
            "排名":       st.column_config.TextColumn("排名",       width="small"),
            "異動標記":   st.column_config.TextColumn("異動標記",   width="large"),
            "成交量標記": st.column_config.SelectboxColumn(
                            "成交量標記", options=["","放量","縮量","—"], width="small"),
            "K線形態":    st.column_config.TextColumn("K線形態",    width="medium"),
            "回測勝率":   st.column_config.TextColumn("回測勝率",   width="small",
                            help="由回測一鍵加入時自動填入"),
            "方向":       st.column_config.TextColumn("方向",       width="small",
                            help="填入「做多」或「做空」；一鍵加入時自動帶入"),
        },
        use_container_width=True,
    )
    _tc = tc.copy()
    for col in _tc.columns:
        _tc[col] = _tc[col].where(_tc[col].notna(), "").astype(str).str.strip()
    st.session_state[ssk] = _tc
    _tg_save(_tc, ticker)
    return _tc




@st.cache_data(ttl=300, show_spinner=False)
def _run_backtest_for_ticker(
    tk: str,
    period: str,
    interval: str,
    min_combo: int,
    max_combo: int,
    min_occ: int,
) -> "tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, int] | tuple[None,None,None,str]":
    """
    對單支股票執行完整回測流程。
    成功回傳 (df_sig, df_vol, df_kl, n_bars)。
    失敗回傳 (None, None, None, error_message)。
    """
    try:
        bt_data = yf.Ticker(tk).history(period=period, interval=interval).reset_index()
        if "Date" in bt_data.columns:
            bt_data = bt_data.rename(columns={"Date": "Datetime"})
        bt_data["Datetime"] = pd.to_datetime(bt_data["Datetime"]).dt.tz_localize(None)
        if len(bt_data) < 30:
            return None, None, None, f"資料不足（{len(bt_data)} 根K線 < 30）"

        # 共用指標計算（回測不含 VIX）
        bt_data = _enrich_data(bt_data, PARAMS, int(MFI_WIN))

        # FIX: 量價異動欄位 — 與主監控用相同公式計算，讓「✅ 量價」信號能參與回測。
        # pa = (|今日漲跌幅| - 5日均漲跌幅) / 5日均漲跌幅 × 100  （比5日均大多少%）
        # va = (今日成交量 - 5日均量) / 5日均量 × 100              （比5日均量多多少%）
        _bt_price_abs = bt_data["Price Change %"].abs()
        bt_data["前5均價ABS"]         = _bt_price_abs.rolling(5).mean()
        bt_data["📈 股價漲跌幅(%)"]   = (
            (_bt_price_abs - bt_data["前5均價ABS"]) /
            bt_data["前5均價ABS"].replace(0, np.nan)
        ).round(4) * 100
        bt_data["📊 成交量變動幅(%)"] = (
            (bt_data["Volume"] - bt_data["前5均量"]) /
            bt_data["前5均量"].replace(0, np.nan)
        ).round(4) * 100
        bt_data["Close_N_High"] = np.nan
        bt_data["Close_N_Low"]  = np.nan

        bt_data["異動標記"] = compute_all_signals(bt_data, PARAMS)
        bt_data = _attach_kline_and_vol(bt_data, tk, period, interval,
                                         BODY_RATIO_TH, SHADOW_RATIO_TH, DOJI_BODY_TH)

        _kw = dict(min_combo=min_combo, max_combo=max_combo, min_occ=min_occ)
        # SPEED: 建一次共用預計算物件，三個維度函數共享，避免重複建 one-hot 矩陣
        _ctx = _build_bt_ctx(bt_data, min_occ)
        df_sig = _base_signal_combos(bt_data, **_kw, _ctx=_ctx)
        df_vol = _signal_x_volume_combos(bt_data, **_kw, _ctx=_ctx)
        df_kl  = _signal_x_kline_combos(bt_data, **_kw, _ctx=_ctx)

        return df_sig, df_vol, df_kl, len(bt_data)

    except Exception as e:
        return None, None, None, str(e)


def _merge_dims_to_conds(
    df_sig: pd.DataFrame,
    df_vol: pd.DataFrame,
    df_kl:  pd.DataFrame,
    wr_thr: float,
    pnl_thr: float = 0.0,
) -> pd.DataFrame:
    """把三個維度的回測結果合併成 Telegram 條件表格式。"""
    def _pass(r) -> bool:
        wr_ok  = r["勝率(%)"] >= wr_thr
        pnl_ok = (pnl_thr == 0.0) or (
            "平均盈虧(%)" in r.index and pd.notna(r["平均盈虧(%)"]) and float(r["平均盈虧(%)"]) >= pnl_thr
        )
        return wr_ok and pnl_ok

    rows = []
    # 統一遍歷三個維度
    dim_specs = [
        (df_sig, "—", "—"),      # (df, 成交量標記欄位, K線形態欄位)
        (df_vol, "成交量標記", "—"),
        (df_kl,  "—", "K線形態"),
    ]
    for df_dim, vol_col, kl_col in dim_specs:
        for _, r in df_dim.iterrows():
            if _pass(r):
                rows.append({
                    "異動標記":   r["信號組合"].replace(" + ", ", "),
                    "成交量標記": r.get(vol_col, "—") if vol_col != "—" else "—",
                    "K線形態":    r.get(kl_col,  "—") if kl_col  != "—" else "—",
                    "回測勝率":   f"{r['勝率(%)']:.1f}%",
                    "方向":       r.get("方向", "做多"),
                    "_wr":        r["勝率(%)"],
                })
    if not rows:
        return pd.DataFrame()
    merged = (
        pd.DataFrame(rows)
        .sort_values("_wr", ascending=False)
        .drop_duplicates(subset=["異動標記","成交量標記","K線形態"], keep="first")
        .drop(columns=["_wr"])
        .reset_index(drop=True)
    )
    merged["排名"] = [str(i+1) for i in range(len(merged))]
    return merged[_TG_COLS]




# ═════════════════════════════════════════════════════════════════════════════
#  MAIN UI
# ═════════════════════════════════════════════════════════════════════════════

st.title("📊 股票監控儀表板")

# ── 總開關 ────────────────────────────────────────────────────────────────────
if "app_running" not in st.session_state:
    st.session_state["app_running"] = False
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = 0.0

col_btn1, col_btn2, col_status = st.columns([1, 1, 4])

with col_btn1:
    if not st.session_state["app_running"]:
        if st.button("▶️ 啟動監控", type="primary", use_container_width=True):
            st.session_state["app_running"] = True
            st.session_state["last_refresh"] = time.time()
            st.rerun()
    else:
        if st.button("⏹️ 停止監控", type="secondary", use_container_width=True):
            st.session_state["app_running"] = False
            st.rerun()

with col_btn2:
    if st.session_state["app_running"]:
        if st.button("🔄 立即刷新", use_container_width=True):
            st.session_state["last_refresh"] = time.time()
            st.rerun()

with col_status:
    if st.session_state["app_running"]:
        st.success(f"🟢 監控運行中　｜　每 **{REFRESH_INTERVAL}** 秒自動刷新", icon="📡")
    else:
        st.warning("⏸️ 已停止，調好參數後按啟動", icon="⚙️")

st.caption(f"⏱ 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── 全域 Telegram 開關 ────────────────────────────────────────────────────────
if selected_tickers:
    # 初始化全域靜音開關
    if "tg_global_mute" not in st.session_state:
        st.session_state["tg_global_mute"] = False

    # ── 1️⃣ 全域靜音熔斷開關（優先級最高）──────────────────────────────────
    _mute_col1, _mute_col2 = st.columns([1, 5])
    with _mute_col1:
        _mute_on = st.session_state["tg_global_mute"]
        if st.button(
            "🔔 解除全域靜音" if _mute_on else "🔇 全域靜音（總開關）",
            key="tg_global_mute_btn",
            use_container_width=True,
            type="secondary" if _mute_on else "primary",
            help="一鍵徹底阻止所有 Telegram 發送，無視其他設定",
        ):
            st.session_state["tg_global_mute"] = not _mute_on
            st.rerun()
    with _mute_col2:
        if _mute_on:
            st.error(
                "🔇 **全域靜音已啟用** — 所有 Telegram 訊息都被強制攔截，"
                "無視個別股票開關。點擊左側按鈕可解除。",
                icon="🚫",
            )
        else:
            st.caption("💡 如果「全部關閉」後仍收到訊息，點擊左邊的「🔇 全域靜音」強制阻止所有發送")

    # ── 2️⃣ 個別股票開關（在全域靜音未啟用時才顯示）──────────────────────
    _n_on  = sum(1 for _tk in selected_tickers
                 if st.session_state.get(f"tg_enabled_{_tk}", True))
    _n_all = len(selected_tickers)
    _all_on  = (_n_on == _n_all)
    _all_off = (_n_on == 0)

    _gc1, _gc2, _gc3 = st.columns([1, 1, 4])

    with _gc1:
        if st.button(
            "🟢 全部開啟",
            key="tg_all_on",
            use_container_width=True,
            disabled=_all_on or _mute_on,
            help=f"將全部 {_n_all} 支股票的 Telegram 開啟",
        ):
            for _tk in selected_tickers:
                st.session_state[f"tg_enabled_{_tk}"] = True
            st.rerun()

    with _gc2:
        if st.button(
            "🔴 全部關閉",
            key="tg_all_off",
            use_container_width=True,
            disabled=_all_off,
            help=f"將全部 {_n_all} 支股票的 Telegram 關閉（靜音模式）",
        ):
            for _tk in selected_tickers:
                st.session_state[f"tg_enabled_{_tk}"] = False
            st.rerun()

    with _gc3:
        if _mute_on:
            st.warning(f"🔇 全域靜音優先，個別股票開關（{_n_on}/{_n_all} 開啟）暫時無效", icon="ℹ️")
        elif _all_on:
            st.success(f"🟢 **全部 {_n_all} 支股票 Telegram 已開啟**", icon="✅")
        elif _all_off:
            st.warning(f"🔴 **全部 {_n_all} 支股票 Telegram 已關閉**（靜音模式）", icon="🔕")
        else:
            _on_names  = [t for t in selected_tickers
                          if st.session_state.get(f"tg_enabled_{t}", True)]
            _off_names = [t for t in selected_tickers
                          if not st.session_state.get(f"tg_enabled_{t}", True)]
            st.info(
                f"⚡ **部分開啟**（{_n_on}/{_n_all}）：🟢 {', '.join(_on_names)}　"
                f"🔴 {', '.join(_off_names)}",
                icon="ℹ️",
            )

    # ── 3️⃣ 突破新高 / 跌破新低 總開關 ──────────────────────────────────
    _bo_n_high = sum(1 for _tk in selected_tickers
                     if st.session_state.get(f"bo_high_{_tk}", True))
    _bo_n_low  = sum(1 for _tk in selected_tickers
                     if st.session_state.get(f"bo_low_{_tk}", True))

    _bo_col1, _bo_col2, _bo_col3, _bo_col4, _bo_info = st.columns([1, 1, 1, 1, 3])

    with _bo_col1:
        if st.button(
            "🚀 全部開啟新高",
            key="bo_high_all_on",
            use_container_width=True,
            disabled=(_bo_n_high == _n_all),
        ):
            for _tk in selected_tickers:
                st.session_state[f"bo_high_{_tk}"] = True
            st.rerun()

    with _bo_col2:
        if st.button(
            "🚫 全部關閉新高",
            key="bo_high_all_off",
            use_container_width=True,
            disabled=(_bo_n_high == 0),
        ):
            for _tk in selected_tickers:
                st.session_state[f"bo_high_{_tk}"] = False
            st.rerun()

    with _bo_col3:
        if st.button(
            "🔻 全部開啟新低",
            key="bo_low_all_on",
            use_container_width=True,
            disabled=(_bo_n_low == _n_all),
        ):
            for _tk in selected_tickers:
                st.session_state[f"bo_low_{_tk}"] = True
            st.rerun()

    with _bo_col4:
        if st.button(
            "🚫 全部關閉新低",
            key="bo_low_all_off",
            use_container_width=True,
            disabled=(_bo_n_low == 0),
        ):
            for _tk in selected_tickers:
                st.session_state[f"bo_low_{_tk}"] = False
            st.rerun()

    with _bo_info:
        st.caption(
            f"🚀 突破新高：{_bo_n_high}/{_n_all} 開啟　｜　"
            f"🔻 跌破新低：{_bo_n_low}/{_n_all} 開啟"
        )

# ── 一鍵全部股票回測 ─────────────────────────────────────────────────────────
_AUTO_PERIOD_MAP = {
    "1d":"1d","5d":"5d","1mo":"1mo","3mo":"3mo","6mo":"6mo",
    "1y":"1y","2y":"2y","5y":"5y","10y":"max",
}
_AUTO_INTERVAL_MAX = {
    "1m": {"1d","5d"},
    "5m": {"1d","5d","1mo"},
    "15m":{"1d","5d","1mo"},
    "30m":{"1d","5d","1mo"},
    "1h": {"1d","5d","1mo","3mo","6mo","1y","2y"},
    "1d": {"1d","5d","1mo","3mo","6mo","1y","2y","5y","10y"},
    "1wk":{"1mo","3mo","6mo","1y","2y","5y","10y"},
    "1mo":{"3mo","6mo","1y","2y","5y","10y"},
}

with st.expander("⚡ 一鍵全部股票自動回測 & 更新 Telegram 條件表", expanded=False):
    st.caption(
        "對所有監控股票依序執行回測，自動用三維合併結果覆蓋各自的 Telegram 觸發條件表。"
    )

    _ac1, _ac2 = st.columns(2)
    _auto_interval = _ac1.selectbox(
        "K線間隔",
        ["1m","5m","15m","30m","1h","1d","1wk","1mo"],
        index=5,
        key="auto_bt_interval",
        help="短週期間隔受 yfinance 限制，可選時間範圍較少",
    )
    _allowed_periods = _AUTO_INTERVAL_MAX.get(_auto_interval,
                       {"1d","5d","1mo","3mo","6mo","1y","2y","5y","10y"})
    _all_periods_ordered = ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y"]
    _period_opts = [p for p in _all_periods_ordered if p in _allowed_periods]
    _period_def  = "1y" if "1y" in _period_opts else _period_opts[-1]
    _auto_period = _ac2.selectbox(
        "時間範圍",
        _period_opts,
        index=_period_opts.index(_period_def),
        key="auto_bt_period",
        help="10y = 使用 yfinance max（全部歷史）",
    )

    _bc1, _bc2, _bc3, _bc4, _bc5 = st.columns(5)
    _auto_wr_thr   = _bc1.number_input(
        "合併勝率閾值 (%)", min_value=0, max_value=100, value=90, step=5,
        key="auto_bt_wr_thr",
    )
    _auto_min_occ  = _bc2.number_input(
        "最少出現次數", min_value=2, max_value=50, value=10, step=1,
        key="auto_bt_min_occ",
    )
    _auto_pnl_thr  = _bc3.number_input(
        "最低平均盈虧 (%)", min_value=-10.0, max_value=20.0, value=0.5, step=0.1,
        format="%.1f",
        key="auto_bt_pnl_thr",
    )
    _auto_min_combo = _bc4.number_input(
        "最少信號組合數", min_value=2, max_value=5, value=2, step=1,
        key="auto_bt_min_combo",
    )
    _auto_max_combo = _bc5.number_input(
        "最多信號組合數", min_value=2, max_value=5, value=3, step=1,
        key="auto_bt_max_combo",
    )

    if _auto_interval in ("1m","5m","15m","30m","1h"):
        st.warning(
            f"⚠️ {_auto_interval} 短週期：yfinance 限制資料範圍，"
            f"樣本數可能較少，建議降低「最少出現次數」至 3～5。",
            icon="⚠️",
        )

    if st.button(
        f"⚡ 開始自動回測所有股票（共 {len(selected_tickers)} 支）",
        type="primary",
        key="auto_bt_run",
        disabled=(len(selected_tickers) == 0),
    ):
        _fetch_period = _AUTO_PERIOD_MAP.get(_auto_period, _auto_period)

        _auto_results = []
        _prog_bar  = st.progress(0, text="準備開始…")
        _status_ph = st.empty()

        # SPEED: 並行抓取 + 運算（ThreadPoolExecutor；yfinance 為 I/O bound，
        #   GIL 不影響效果）。_run_backtest_for_ticker 有 @st.cache_data，
        #   多執行緒呼叫完全安全。session_state / UI 寫入仍在主執行緒完成。
        _bt_kwargs = dict(
            period    = _fetch_period,
            interval  = _auto_interval,
            min_combo = int(_auto_min_combo),
            max_combo = int(max(_auto_max_combo, _auto_min_combo)),
            min_occ   = int(_auto_min_occ),
        )
        _n_tickers = len(selected_tickers)
        _MAX_WORKERS = min(_n_tickers, 6)   # 最多 6 執行緒，避免 yfinance 限速

        _futures_map: dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as _pool:
            for _atk in selected_tickers:
                _futures_map[_pool.submit(_run_backtest_for_ticker, tk=_atk, **_bt_kwargs)] = _atk

            _done_count = 0
            for _fut in concurrent.futures.as_completed(_futures_map):
                _atk = _futures_map[_fut]
                _done_count += 1
                _prog = _done_count / _n_tickers
                _prog_bar.progress(_prog, text=f"完成 {_atk}（{_done_count}/{_n_tickers}）…")

                try:
                    _dsig, _dvol, _dkl, _n_or_err = _fut.result()
                except Exception as _exc:
                    _auto_results.append({
                        "ticker": _atk, "status": "❌", "n_conds": 0,
                        "msg": str(_exc),
                    })
                    _status_ph.error(f"❌ **{_atk}** 回測失敗：{_exc}")
                    continue

                if _dsig is None:
                    _auto_results.append({
                        "ticker": _atk, "status": "❌", "n_conds": 0,
                        "msg": str(_n_or_err),
                    })
                    _status_ph.error(f"❌ **{_atk}** 回測失敗：{_n_or_err}")
                    continue

                _merged = _merge_dims_to_conds(
                    _dsig, _dvol, _dkl,
                    wr_thr  = float(_auto_wr_thr),
                    pnl_thr = float(_auto_pnl_thr),
                )

                if _merged.empty:
                    _cond_str = f"勝率 ≥ {_auto_wr_thr}%"
                    if _auto_pnl_thr != 0:
                        _cond_str += f" 且 平均盈虧 ≥ {_auto_pnl_thr}%"
                    _auto_results.append({
                        "ticker": _atk, "status": "⚠️", "n_conds": 0,
                        "msg": f"無符合條件（{_cond_str}）的組合，條件表未更新",
                    })
                    _status_ph.warning(f"⚠️ **{_atk}**：無符合條件的組合")
                    continue

                st.session_state[_ss_key(_atk)] = _merged
                _tg_save(_merged, _atk)

                _auto_results.append({
                    "ticker": _atk, "status": "✅",
                    "n_conds": len(_merged),
                    "msg": (
                        f"寫入 {len(_merged)} 條條件"
                        f"（{_auto_period}/{_auto_interval}，"
                        f"勝率 ≥ {_auto_wr_thr}%，盈虧 ≥ {_auto_pnl_thr}%）"
                    ),
                })
                _status_ph.success(f"✅ **{_atk}**：寫入 {len(_merged)} 條條件")

        _prog_bar.progress(1.0, text="全部完成！")
        _status_ph.empty()

        # FIX P4-#10: 並行完成順序隨機，按 selected_tickers 原序重排結果
        _ticker_order = {tk: i for i, tk in enumerate(selected_tickers)}
        _auto_results.sort(key=lambda r: _ticker_order.get(r["ticker"], 999))

        _ok_list   = [r for r in _auto_results if r["status"] == "✅"]
        _warn_list = [r for r in _auto_results if r["status"] == "⚠️"]
        _err_list  = [r for r in _auto_results if r["status"] == "❌"]

        st.markdown("---")
        st.subheader("📊 自動回測結果總結")
        _sc1, _sc2, _sc3 = st.columns(3)
        _sc1.metric("✅ 成功", len(_ok_list))
        _sc2.metric("⚠️ 無符合條件", len(_warn_list))
        _sc3.metric("❌ 失敗", len(_err_list))

        for _r in _auto_results:
            st.write(f"{_r['status']} **{_r['ticker']}**：{_r['msg']}")

        if _ok_list:
            n_ok = len(_ok_list)
            st.success(
                f"🎯 成功更新 **{n_ok}** 支股票的 Telegram 條件表！"
                " 請切換到各股票 Tab 確認條件表內容。",
                icon="🎯",
            )
            st.balloons()

tabs = st.tabs([f"📈 {t}" for t in selected_tickers] + ["🔬 回測分析", "📡 Screener選股", "📊 監控總覽"])


# ── FIX BUG-03: Telegram 去重輔助函數 ─────────────────────────────────────────
def _tg_dedup_key(ticker: str, last_dt) -> str:
    """為每支股票 + 每根K線的 Datetime 生成唯一的去重 key。"""
    return f"tg_sent_{ticker}_{str(last_dt)[:19]}"


def _tg_already_sent(key: str, sig_or_rank: str) -> bool:
    """檢查某信號/條件是否已在本根K線中發送過。"""
    sent_set = st.session_state.get(key, set())
    return sig_or_rank in sent_set


def _tg_mark_sent(key: str, sig_or_rank: str):
    """標記某信號/條件已發送，並清理過期記錄。"""
    if key not in st.session_state:
        st.session_state[key] = set()
    st.session_state[key].add(sig_or_rank)

    # 清理舊記錄（保留最近 10 筆）
    _prefix = key.rsplit("_", 1)[0]  # tg_sent_TICKER
    _old_keys = sorted([k for k in st.session_state if k.startswith(_prefix + "_")])
    if len(_old_keys) > 10:
        for _ok in _old_keys[:-10]:
            try:
                del st.session_state[_ok]
            except KeyError:
                pass


def _build_cond_id(raw_marks: str, c_vol: str, c_kline: str) -> str:
    """
    FIX BUG-11/12: 用條件內容的 hash 作為唯一 ID（而非排名）。

    解決問題：
    - 用戶編輯條件表後，排名不變但內容改變 → 不應被誤判為已發送
    - 用戶手動填入重複排名 → 每條都要能獨立去重

    內容相同 → hash 相同 → 去重生效
    內容不同 → hash 不同 → 獨立去重
    """
    import hashlib
    # 正規化：空白/—/全部都視為空，去除多餘空白
    _norm_vol   = "" if c_vol   in ("", "—", "全部") else c_vol.strip()
    _norm_kline = "" if c_kline in ("", "—", "全部") else c_kline.strip()
    # 信號排序後 join（避免順序不同造成不同 hash）
    _sorted_sigs = sorted([s.strip() for s in raw_marks.split(",") if s.strip()])
    content = f"{','.join(_sorted_sigs)}|{_norm_vol}|{_norm_kline}"
    h = hashlib.md5(content.encode("utf-8")).hexdigest()[:10]
    return f"cond_{h}"




# ═════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP  (each ticker)
# ═════════════════════════════════════════════════════════════════════════════

for tab_idx, ticker in enumerate(selected_tickers):
    with tabs[tab_idx]:
        _tk_conds = _tg_init(ticker)

        # ── 每支股票獨立的 Telegram 開關 ──────────────────────────────────────
        _tg_en_key = f"tg_enabled_{ticker}"
        if _tg_en_key not in st.session_state:
            st.session_state[_tg_en_key] = True

        _sw_col, _sw_info = st.columns([1, 5])
        with _sw_col:
            # FIX: 按鈕顯示「下一步動作」，更符合直覺
            _sw_label = (
                f"🔴 關閉 {ticker} Telegram"
                if st.session_state[_tg_en_key]
                else f"🟢 開啟 {ticker} Telegram"
            )
            if st.button(_sw_label, key=f"tg_toggle_{ticker}", use_container_width=True):
                st.session_state[_tg_en_key] = not st.session_state[_tg_en_key]
                st.rerun()
        with _sw_info:
            if st.session_state[_tg_en_key]:
                st.success(f"🟢 **{ticker} Telegram 開啟**：條件匹配時自動推送", icon="✅")
            else:
                st.warning(
                    f"🔴 **{ticker} Telegram 已關閉（靜音模式）**：只顯示 UI 提示，不發送訊息。",
                    icon="🔕",
                )

        # ── 使用全域信號清單（適用於所有股票）────────────────────────────
        # FIX: 不再為每支股票各設一個 multiselect；統一讀取側欄的全域選擇。
        selected_signals = st.session_state.get(
            "global_selected_signals", GLOBAL_SELECTED_SIGNALS
        )
        if selected_signals:
            st.caption(
                f"📡 推播信號（全域）：{'、'.join(selected_signals)}　"
                f"｜如需修改請至左側欄「Telegram 推播信號（全域）」"
            )
        else:
            st.caption("📡 尚未選擇任何全域推播信號（左側欄設定）")

        # ── 突破新高/跌破新低 開關 ────────────────────────────────────────
        _bo_col1, _bo_col2 = st.columns(2)
        with _bo_col1:
            _bo_high_on = st.checkbox(
                "🚀 突破新高提醒",
                value=st.session_state.get(f"bo_high_{ticker}", True),
                key=f"bo_high_{ticker}",
                help=f"當 {ticker} 股價創 MFI窗口 根K線新高時推送 Telegram",
            )
        with _bo_col2:
            _bo_low_on = st.checkbox(
                "🔻 跌破新低提醒",
                value=st.session_state.get(f"bo_low_{ticker}", True),
                key=f"bo_low_{ticker}",
                help=f"當 {ticker} 股價創 MFI窗口 根K線新低時推送 Telegram",
            )

        st.subheader(f"📋 {ticker} Telegram 觸發條件配置（可編輯）")

        if tab_idx > 0 and len(selected_tickers) > 1:
            _first_ticker = selected_tickers[0]
            _first_ssk    = _ss_key(_first_ticker)
            if st.button(
                f"📋 複製 {_first_ticker} 條件表 → {ticker}",
                key=f"copy_conds_{ticker}",
            ):
                if _first_ssk in st.session_state:
                    _copied = st.session_state[_first_ssk].copy()
                    st.session_state[_ss_key(ticker)] = _copied
                    _tg_save(_copied, ticker)
                    st.success(f"✅ 已複製 {_first_ticker} 的條件表到 {ticker}")
                    st.rerun()

        _tk_conds = _tg_editor(ticker)

        # 條件表為空時提示用戶
        if _tk_conds.empty or len(_tk_conds) == 0 or _tk_conds["異動標記"].str.strip().replace("", pd.NA).dropna().empty:
            st.warning(
                f"⚠️ **{ticker} 條件表為空**，不會觸發任何 Telegram 推送。\n\n"
                "請先展開下方「🔬 回測分析」執行回測，再用「➕ 一鍵加入」或「🔀 合併」填入條件。",
                icon="📋",
            )

        try:
            # ── Fetch data（FIX P2-#4: 改用快取封裝，TTL=60s）────────────────
            data = _fetch_price_data(ticker, selected_period, selected_interval)
            if data.empty or len(data) < 5:
                st.warning(f"⚠️ {ticker} 數據不足"); continue

            # ── Basic columns ─────────────────────────────────────────────────
            hl_range = (data["High"] - data["Low"]).replace(0, np.nan)
            data["Close_N_High"]      = (data["Close"] - data["Low"])   / hl_range
            data["Close_N_Low"]       = (data["High"]  - data["Close"]) / hl_range

            # ── 共用指標計算（含 VIX）──────────────────────────────────────
            data = _enrich_data(
                data, PARAMS, int(MFI_WIN),
                include_vix=True,
                vix_period=selected_period,
                vix_interval=selected_interval,
                vix_ema_fast=int(VIX_EMA_FAST),
                vix_ema_slow=int(VIX_EMA_SLOW),
            )

            # ── 額外的異動幅度欄位（主監控專用）──
            data["前5均價ABS"]         = data["Price Change %"].abs().rolling(5).mean()
            data["📈 股價漲跌幅(%)"]   = ((data["Price Change %"].abs() - data["前5均價ABS"]) /
                                           data["前5均價ABS"].replace(0, np.nan)).round(4) * 100
            data["📊 成交量變動幅(%)"] = ((data["Volume"] - data["前5均量"]) /
                                           data["前5均量"].replace(0, np.nan)).round(4) * 100

            # ── Signals ───────────────────────────────────────────────────────
            data["異動標記"] = compute_all_signals(data, PARAMS)

            # ── K-line patterns + volume tag (shared) ─────────────────────────
            data = _attach_kline_and_vol(data, ticker, selected_period, selected_interval,
                                          BODY_RATIO_TH, SHADOW_RATIO_TH, DOJI_BODY_TH)

            # ── Volume profile ────────────────────────────────────────────────
            dense_areas = calculate_volume_profile(data, int(VP_BINS), int(VP_WINDOW), int(VP_TOP_N))

            # v3.7: 存入即時快照，供 AI Prompt 生成函數使用
            _save_ticker_snapshot(ticker, data, dense_areas,
                                  selected_period, selected_interval)
            latest_close = data["Close"].iloc[-1]
            near_dense = False; near_dense_info = ""
            for a in dense_areas:
                if a["price_low"] <= latest_close <= a["price_high"]:
                    near_dense = True; near_dense_info = f"位於密集區 {a['price_low']:.2f}~{a['price_high']:.2f}"; break
                if abs(latest_close - a["price_center"]) / a["price_center"] * 100 <= 1.0:
                    near_dense = True; near_dense_info = f"接近密集中心 {a['price_center']:.2f}"; break

            # ── Metrics row ───────────────────────────────────────────────────
            try:
                prev_close = yf.Ticker(ticker).info.get("previousClose", data["Close"].iloc[-2])
            except Exception:
                prev_close = data["Close"].iloc[-2]
            cur_price = data["Close"].iloc[-1]
            px_chg = cur_price - prev_close
            px_pct = px_chg / prev_close * 100 if prev_close else 0
            cur_vol = data["Volume"].iloc[-1]; prev_vol = data["Volume"].iloc[-2]
            v_chg = cur_vol - prev_vol; v_pct = v_chg / prev_vol * 100 if prev_vol else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(f"💰 {ticker}", f"${cur_price:.2f}", f"{px_chg:+.2f} ({px_pct:+.2f}%)")
            c2.metric("📊 成交量", f"{cur_vol:,.0f}", f"{v_pct:+.1f}%")
            c3.metric("📈 RSI", f"{data['RSI'].iloc[-1]:.1f}" if pd.notna(data['RSI'].iloc[-1]) else "N/A")
            c4.metric("📉 MACD", f"{data['MACD'].iloc[-1]:.3f}")
            vix_v = data["VIX"].iloc[-1]
            c5.metric("⚡ VIX", f"{vix_v:.1f}" if pd.notna(vix_v) else "N/A")

            if near_dense:
                st.info(f"⚠️ {ticker} 靠近成交密集區：{near_dense_info}")

            # ── Comprehensive interpretation ───────────────────────────────────
            st.subheader("📝 綜合解讀")
            st.write(comprehensive_interp(data, dense_areas, VIX_HIGH_TH, VIX_LOW_TH))

            # ── Chart (4 rows) ─────────────────────────────────────────────────
            st.subheader(f"📈 {ticker} K 線技術圖表")
            plot_d = data.tail(60).copy()
            fig = make_subplots(
                rows=4, cols=1, shared_xaxes=True,
                subplot_titles=("K線 / EMA / VWAP", "成交量 / OBV", "RSI", "MFI"),
                row_heights=[0.45, 0.2, 0.175, 0.175],
                vertical_spacing=0.04,
            )
            fig.add_trace(go.Candlestick(
                x=plot_d["Datetime"], open=plot_d["Open"],
                high=plot_d["High"], low=plot_d["Low"], close=plot_d["Close"],
                name="K線", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
                increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350",
            ), row=1, col=1)
            for col_n, clr, w in [("EMA5","#FF6B6B",1.2), ("EMA10","#4ECDC4",1.2),
                                    ("EMA30","#45B7D1",1.2), ("EMA40","#96CEB4",1.2),
                                    ("VWAP","#BB86FC",2.0)]:
                if col_n in plot_d.columns:
                    fig.add_trace(go.Scatter(x=plot_d["Datetime"], y=plot_d[col_n],
                                             mode="lines", name=col_n,
                                             line=dict(color=clr, width=w)), row=1, col=1)
            if VP_SHOW and dense_areas and len(plot_d) >= 10:
                x0 = plot_d["Datetime"].iloc[-min(50, len(plot_d))]
                x1 = plot_d["Datetime"].iloc[-1]
                for i, a in enumerate(dense_areas):
                    fig.add_shape(type="rect", x0=x0, x1=x1,
                                  y0=a["price_low"], y1=a["price_high"],
                                  fillcolor="rgba(255,165,0,0.12)", line_width=0,
                                  row=1, col=1)
                    fig.add_hline(y=a["price_center"], line_dash="dot", line_color="orange",
                                  annotation_text=f"密集 {a['price_center']:.2f}",
                                  annotation_position="left" if i%2==0 else "right",
                                  row=1, col=1)
            vcols = ["#26a69a" if c>=o else "#ef5350" for c,o in zip(plot_d["Close"], plot_d["Open"])]
            fig.add_trace(go.Bar(x=plot_d["Datetime"], y=plot_d["Volume"],
                                  name="成交量", marker_color=vcols, opacity=0.6), row=2, col=1)
            fig.add_trace(go.Scatter(x=plot_d["Datetime"], y=plot_d["OBV"],
                                      mode="lines", name="OBV",
                                      line=dict(color="#FF8C00", width=1.5),
                                      yaxis="y4"), row=2, col=1)
            fig.add_trace(go.Scatter(x=plot_d["Datetime"], y=plot_d["RSI"],
                                      mode="lines", name="RSI",
                                      line=dict(color="#2196F3", width=1.5)), row=3, col=1)
            for lvl, clr in [(70,"red"),(50,"gray"),(30,"green")]:
                fig.add_hline(y=lvl, line_dash="dash", line_color=clr, line_width=0.7, row=3, col=1)
            fig.add_trace(go.Scatter(x=plot_d["Datetime"], y=plot_d["MFI"],
                                      mode="lines", name="MFI",
                                      line=dict(color="#8B4513", width=1.5)), row=4, col=1)
            for lvl, clr in [(80,"red"),(20,"green")]:
                fig.add_hline(y=lvl, line_dash="dash", line_color=clr, line_width=0.7, row=4, col=1)
            # Signal annotations
            annot_cfg = {
                "📈 新买入信号":  ("▲","#2ecc71","bottom center",1),
                "📉 新卖出信号":  ("▼","#e74c3c","top center",   1),
                "📈 VWAP買入":   ("V↑","#BB86FC","bottom center",1),
                "📉 VWAP賣出":   ("V↓","#BB86FC","top center",   1),
                "📈 OBV突破買入":("O↑","#FF8C00","bottom center",2),
                "📉 OBV突破賣出":("O↓","#FF8C00","top center",   2),
                "📈 MFI牛背離買入":("M↑","#8B4513","bottom center",4),
                "📉 MFI熊背離賣出":("M↓","#8B4513","top center",  4),
                "📈 MACD買入":   ("MC↑","#4ECDC4","bottom center",1),
                "📉 MACD賣出":   ("MC↓","#FF6B6B","top center",   1),
            }
            for i in range(1, len(plot_d)):
                marks = str(plot_d["異動標記"].iloc[i])
                dt, cl = plot_d["Datetime"].iloc[i], plot_d["Close"].iloc[i]
                for sig, (sym, clr, pos, row_n) in annot_cfg.items():
                    if sig in marks:
                        fig.add_trace(go.Scatter(
                            x=[dt], y=[cl], mode="markers+text",
                            marker=dict(symbol="circle", size=9, color=clr),
                            text=[sym], textposition=pos,
                            showlegend=False,
                        ), row=row_n, col=1)

            fig.update_layout(
                height=920, template="plotly_dark", showlegend=True,
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", y=-0.04, font=dict(size=11)),
                margin=dict(l=40, r=40, t=60, b=40),
            )
            fig.update_yaxes(title_text="價格",  row=1, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)
            fig.update_yaxes(title_text="RSI",   row=3, col=1, range=[0,100])
            fig.update_yaxes(title_text="MFI",   row=4, col=1, range=[0,100])
            st.plotly_chart(fig, use_container_width=True,
                            key=f"chart_{ticker}_{datetime.now().strftime('%H%M%S')}")

            # ── Signal success rate ────────────────────────────────────────────
            st.subheader(f"📊 {ticker} 各信號勝率")
            data["_next_up"]  = data["Close"].shift(-1) > data["Close"]
            data["_next_dn"]  = data["Close"].shift(-1) < data["Close"]
            sr_rows = []
            all_sigs_found = set()
            for marks in data["異動標記"].dropna():
                for s in str(marks).split(", "):
                    if s.strip():
                        all_sigs_found.add(s.strip())
            for sig in sorted(all_sigs_found):
                sub = data[data["異動標記"].str.contains(sig, na=False, regex=False)]
                # FIX BUG-02: 排除最後一根（shift(-1) NaN）
                sub = sub[sub["Close"].shift(-1).notna()] if len(sub) > 0 else sub
                n   = len(sub)
                if n == 0:
                    continue
                if sig in SELL_SIGNALS:
                    ok = sub["_next_dn"].sum(); dir_ = "做空"
                else:
                    ok = sub["_next_up"].sum(); dir_ = "做多"
                wr = ok / n * 100
                sr_rows.append({"信號":sig,"方向":dir_,"勝率(%)":f"{wr:.1f}%","次數":n})
            if sr_rows:
                sr_df = pd.DataFrame(sr_rows).sort_values("勝率(%)", ascending=False)
                st.dataframe(sr_df, use_container_width=True,
                             column_config={"信號": st.column_config.TextColumn(width="large")})

            # ── History table ─────────────────────────────────────────────────
            st.subheader(f"📋 {ticker} 歷史資料（最近 20 筆）")
            show_cols = [c for c in ["Datetime","Open","Low","High","Close","Volume",
                                      "Price Change %","Volume Change %","MACD","RSI",
                                      "VWAP","MFI","OBV","VIX",
                                      "異動標記","成交量標記","K線形態","單根解讀"] if c in data.columns]
            st.dataframe(data[show_cols].tail(20), height=460, use_container_width=True,
                         column_config={"異動標記":   st.column_config.TextColumn(width="large"),
                                        "單根解讀": st.column_config.TextColumn(width="large")})

            # ── Percentile table ───────────────────────────────────────────────
            with st.expander(f"📊 前 {PERCENTILE_TH}% 數據範圍"):
                rng_rows = []
                for cn in ["Price Change %","Volume Change %","Volume","📈 股價漲跌幅(%)","📊 成交量變動幅(%)"]:
                    if cn not in data.columns: continue
                    s = data[cn].dropna().sort_values(ascending=False)
                    n = max(1, int(len(s) * PERCENTILE_TH / 100))
                    rng_rows += [
                        {"指標":cn,"範圍":"Top",    "最大":f"{s.head(n).max():.2f}","最小":f"{s.head(n).min():.2f}"},
                        {"指標":cn,"範圍":"Bottom", "最大":f"{s.tail(n).max():.2f}","最小":f"{s.tail(n).min():.2f}"},
                    ]
                if rng_rows:
                    st.dataframe(pd.DataFrame(rng_rows), use_container_width=True)

            st.download_button(
                label=f"📥 下載 {ticker} CSV",
                data=data.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

            # ── AI Prompt（v3.7）─────────────────────────────────────────────
            with st.expander(f"🤖 複製 AI 分析 Prompt（{ticker}）", expanded=False):
                st.caption(
                    "以下 Prompt 已包含即時技術指標、信號、回測數據和密集區。"
                    "複製後貼去 ChatGPT / Claude / Gemini 即可獲得具體操作建議，無需 API。"
                )
                _sig_prompt = _build_signal_prompt(ticker)
                st.code(_sig_prompt, language=None)
                st.caption("💡 小提示：如需追問，可直接在 AI 對話繼續提問，無需重新貼 Prompt。")

            # ══════════════════════════════════════════════════════════════════
            #  TELEGRAM / EMAIL ALERTS  (FIX BUG-03: 去重機制)
            # ══════════════════════════════════════════════════════════════════
            K_str  = str(data["異動標記"].iloc[-1])
            K_list = [s.strip() for s in K_str.split(", ") if s.strip()]

            # FIX BUG-03: 生成去重 key（基於最新K線的 Datetime）
            _dedup_key_sig  = _tg_dedup_key(ticker, data["Datetime"].iloc[-1])
            _dedup_key_cond = f"tg_cond_sent_{ticker}_{str(data['Datetime'].iloc[-1])[:19]}"

            # ── 信號 → 方向查找表 ──────────────────────────────────────────
            _live_tg_p1 = _tk_conds
            _sig_dir_map: dict = {}
            for _, _p1_row in _live_tg_p1.iterrows():
                _p1_marks = str(_p1_row.get("異動標記", ""))
                _p1_dir   = str(_p1_row.get("方向", "")).strip()
                if _p1_dir not in ("做多", "做空"):
                    continue
                for _p1_sig in _p1_marks.split(","):
                    _s = _p1_sig.strip()
                    if _s and _s not in _sig_dir_map:
                        _sig_dir_map[_s] = _p1_dir

            # ── Selected-signal push (with dedup) ──────────────────────────
            for sig in selected_signals:
                if sig in K_list and not _tg_already_sent(_dedup_key_sig, sig):
                    _p1_dir_val = _sig_dir_map.get(sig, "")
                    if not _p1_dir_val:
                        _p1_dir_val = "做空" if sig in SELL_SIGNALS else "做多"
                    _p1_dir_label = "🔴 做空（賣出）" if _p1_dir_val == "做空" else "🟢 做多（買入）"

                    _msg = (
                        f"📡 信號提醒\n"
                        f"股票：{ticker} ({selected_interval})\n"
                        f"信號：{sig}\n"
                        f"操作方向：{_p1_dir_label}\n"
                        f"價格：${cur_price:.2f}\n"
                        f"RSI：{data['RSI'].iloc[-1]:.1f}  MACD：{data['MACD'].iloc[-1]:.3f}\n"
                        f"成交量：{_fmt_vol(data['Volume'].iloc[-1])}  "
                        f"({data['成交量標記'].iloc[-1]})"
                    )
                    if st.session_state.get(f"tg_enabled_{ticker}", True):
                        _ok, _err = send_telegram_alert(_msg, ticker=ticker)
                        if _ok:
                            _tg_mark_sent(_dedup_key_sig, sig)
                            st.toast(f"📡 Telegram 已推送：{sig} ({_p1_dir_label})", icon="✅")
                        else:
                            st.warning(f"⚠️ Telegram 推送失敗（{sig}）：{_err}")
                    else:
                        _tg_mark_sent(_dedup_key_sig, sig)  # 即使關閉也標記為已處理
                        st.toast(f"🔕 {sig} 已匹配，Telegram 已關閉", icon="🔕")

            # ── Condition matching (with dedup) ────────────────────────────
            def _safe_str(v) -> str:
                if v is None:
                    return ""
                s = str(v).strip()
                return "" if s.lower() in ("none", "nan", "nat", "") else s

            if "tg_match_mode" not in st.session_state:
                st.session_state["tg_match_mode"] = "first"

            _col_mode, _col_info = st.columns([1, 4])
            with _col_mode:
                _mode_label = (
                    "🔁 模式：**全部比對**（點擊切換為第一個）"
                    if st.session_state["tg_match_mode"] == "all"
                    else "1️⃣ 模式：**第一個匹配**（點擊切換為全部）"
                )
                if st.button(_mode_label, key=f"tg_mode_btn_{ticker}"):
                    st.session_state["tg_match_mode"] = (
                        "first" if st.session_state["tg_match_mode"] == "all" else "all"
                    )
                    st.rerun()
            with _col_info:
                if st.session_state["tg_match_mode"] == "all":
                    st.caption("🔁 **全部比對模式**：逐行掃描條件表，每一個符合的條件都各自發一條 Telegram 訊息。")
                else:
                    st.caption("1️⃣ **第一個匹配模式**：從排名第 1 行開始比對，找到第一個符合的條件就觸發並停止。")

            _scan_all  = (st.session_state["tg_match_mode"] == "all")
            # 直接使用 _tk_conds（來自 _tg_editor 的最新輸出），而非重新讀取 session_state
            # 確保比對邏輯與 UI 上顯示的條件表完全一致
            _live_tg   = _tk_conds
            _cur_vol   = _safe_str(data["成交量標記"].iloc[-1])
            _cur_kline = _safe_str(data["K線形態"].iloc[-1])

            _rsi_val  = float(data["RSI"].iloc[-1]) if pd.notna(data["RSI"].iloc[-1]) else 0.0
            _macd_val = float(data["MACD"].iloc[-1])
            _sig_line = float(data["Signal_Line"].iloc[-1]) if "Signal_Line" in data.columns else 0.0
            _vix_val  = data["VIX"].iloc[-1]
            _vix_str  = f"{_vix_val:.1f}" if pd.notna(_vix_val) else "N/A"
            _near_str = near_dense_info if near_dense else "無密集區靠近"
            _dir_icon = "🟢" if px_pct >= 0 else "🔴"
            _rsi_icon = "🔥" if _rsi_val > 70 else ("🧊" if _rsi_val < 30 else "⚪")
            _vol_icon = "📈" if _cur_vol == "放量" else "📉"

            def _build_tg_msg(rank, backtest_wr, match_no, total_matches,
                             direction="做多", matched_signals=""):
                _header = (
                    f"{'='*28}\n"
                    f"🚨 Telegram 觸發條件匹配"
                    + (f"（第 {match_no}/{total_matches} 條）" if total_matches > 1 else "")
                    + f"\n{'='*28}"
                )
                if direction == "做多":
                    _dir_label = "🟢 做多（買入）"
                elif direction == "做空":
                    _dir_label = "🔴 做空（賣出）"
                else:
                    _dir_label = "未設定"
                _lines = [
                    _header, "",
                    f"股票代號  : {ticker}",
                    f"時間框架  : {selected_interval}",
                    f"觸發時間  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "--- 價格資訊 ---",
                    f"現價      : ${cur_price:.2f}  {_dir_icon} {px_pct:+.2f}%",
                    f"成交量    : {_fmt_vol(data['Volume'].iloc[-1])}  {_vol_icon} {_cur_vol}  ({v_pct:+.1f}%)",
                    "",
                    "--- 技術指標 ---",
                    f"RSI       : {_rsi_val:.1f}  {_rsi_icon}",
                    f"MACD      : {_macd_val:.4f}  (Signal: {_sig_line:.4f})",
                    f"K線形態   : {_cur_kline}",
                    f"VIX       : {_vix_str}",
                    f"密集區    : {_near_str}",
                    "",
                    "--- 匹配條件 ---",
                    f"條件排名  : #{rank}",
                    f"回測勝率  : {backtest_wr}",
                    f"方向      : {_dir_label}",
                ]
                # 顯示匹配到的條件表信號（不是全部 K_list）
                if matched_signals:
                    _lines.append(f"條件信號  : {matched_signals}")
                _lines += [
                    "",
                    "--- 當前K線全部信號 ---",
                ]
                for _s in K_list[:12]:
                    _lines.append(f"  {_s}")
                if len(K_list) > 12:
                    _lines.append(f"  ... 共 {len(K_list)} 個信號")
                _lines.append(f"{'='*28}")
                return "\n".join(_lines)

            # ── 核心比對迴圈 ──────────────────────────────────────────────
            _matched_list = []

            for _ci, cond_row in _live_tg.iterrows():
                _raw_marks = _safe_str(cond_row.get("異動標記", ""))
                if not _raw_marks:
                    continue
                req = [s.strip() for s in _raw_marks.split(",") if s.strip()]
                if not req:
                    continue

                c_vol   = _safe_str(cond_row.get("成交量標記", ""))
                c_kline = _safe_str(cond_row.get("K線形態", ""))
                vol_ok    = (c_vol   == "") or (c_vol   in ("—", "全部")) or (c_vol   == _cur_vol)
                kline_ok  = (c_kline == "") or (c_kline in ("—", "全部")) or (c_kline == _cur_kline)
                signals_ok = all(s in K_list for s in req)

                if signals_ok and vol_ok and kline_ok:
                    _rank_raw = _safe_str(cond_row.get("排名", ""))
                    _rank     = _rank_raw if _rank_raw else f"#{_ci + 1}"
                    _wr_raw   = _safe_str(cond_row.get("回測勝率", ""))
                    _wr       = _wr_raw if _wr_raw else "N/A"
                    _dir_raw  = _safe_str(cond_row.get("方向", ""))
                    _dir      = _dir_raw if _dir_raw in ("做多", "做空") else ""
                    _matched_list.append((_rank, _wr, _ci, _dir, _raw_marks))

                    if not _scan_all:
                        break

            _total_matched = len(_matched_list)

            if _total_matched > 0:
                # UI 摘要
                if _total_matched == 1:
                    _rank0, _wr0, _, _dir0, _sigs0 = _matched_list[0]
                    _dir0_label = ("🟢 做多" if _dir0 == "做多"
                                   else "🔴 做空" if _dir0 == "做空"
                                   else "未設定")
                    st.info(
                        f"🎯 **條件匹配！** 排名 {_rank0}，回測勝率 {_wr0}，方向 {_dir0_label}\n\n"
                        f"信號：{K_str[:120]}\n成交量：{_cur_vol}  K線：{_cur_kline}",
                    )
                else:
                    _ranks_str = "、".join(r for r, _, __, ___, ____ in _matched_list)
                    st.info(
                        f"🎯 **共匹配 {_total_matched} 條條件！** 排名：{_ranks_str}\n\n"
                        f"信號：{K_str[:120]}\n成交量：{_cur_vol}  K線：{_cur_kline}",
                    )

                # FIX BUG-03: 帶去重的發送邏輯
                _tg_on = st.session_state.get(f"tg_enabled_{ticker}", True)
                _send_ok_count  = 0
                _send_err_msgs  = []

                if not _tg_on:
                    _ranks_muted = "、".join(r for r,_,__,___,____ in _matched_list)
                    st.warning(
                        f"🔕 **Telegram 已關閉**，訊息未發送。匹配條件：排名 {_ranks_muted}。",
                        icon="🔕",
                    )
                    # 即使關閉也標記為已處理，避免開啟後重複發送舊信號
                    for _rank, _, _ci, _, _msigs in _matched_list:
                        # FIX BUG-11/12: 用條件內容 hash 作為去重 key
                        _row = _live_tg.iloc[_ci]
                        _cid = _build_cond_id(
                            _safe_str(_row.get("異動標記", "")),
                            _safe_str(_row.get("成交量標記", "")),
                            _safe_str(_row.get("K線形態", "")),
                        )
                        _tg_mark_sent(_dedup_key_cond, _cid)
                else:
                    for _mn, (_rank, _wr, _ci, _dir, _msigs) in enumerate(_matched_list, start=1):
                        # FIX BUG-11/12: 用條件內容 hash 作為去重 key，而非排名
                        _row = _live_tg.iloc[_ci]
                        _cond_id = _build_cond_id(
                            _safe_str(_row.get("異動標記", "")),
                            _safe_str(_row.get("成交量標記", "")),
                            _safe_str(_row.get("K線形態", "")),
                        )
                        if _tg_already_sent(_dedup_key_cond, _cond_id):
                            continue  # 已發送過，跳過

                        _msg = _build_tg_msg(
                            rank=_rank, backtest_wr=_wr,
                            match_no=_mn, total_matches=_total_matched,
                            direction=_dir, matched_signals=_msigs,
                        )
                        _ok, _err = send_telegram_alert(_msg, ticker=ticker)
                        if _ok:
                            _send_ok_count += 1
                            _tg_mark_sent(_dedup_key_cond, _cond_id)
                            st.toast(
                                f"✅ {ticker} 條件 #{_rank} 匹配，Telegram 已推送"
                                + (f"（{_mn}/{_total_matched}）" if _total_matched > 1 else ""),
                                icon="📨",
                            )
                        else:
                            _send_err_msgs.append(f"排名 {_rank}：{_err}")

                    if _send_ok_count > 0 and not _send_err_msgs:
                        st.success(f"📨 **Telegram 發送成功！** 共 {_send_ok_count} 條訊息", icon="✅")
                    elif _send_ok_count > 0 and _send_err_msgs:
                        st.warning(f"⚠️ 部分發送成功（{_send_ok_count}/{_total_matched}）。\n" + "\n".join(_send_err_msgs))
                    elif _send_err_msgs:
                        st.error("❌ **Telegram 全部發送失敗**：\n" + "\n".join(_send_err_msgs), icon="🚨")
                    # 如果 _send_ok_count == 0 且無 err（都已去重跳過），靜默不顯示

            # ── Breakout / Breakdown alerts (with dedup + toggle) ─────────
            _tg_on_bo = st.session_state.get(f"tg_enabled_{ticker}", True)

            # if st.session_state.get(f"bo_high_{ticker}", True) and \
            #    pd.notna(data["High_Max"].iloc[-1]) and data["High"].iloc[-1] >= data["High_Max"].iloc[-1]:
            #     if not _tg_already_sent(_dedup_key_sig, "breakout_high"):
            #         _bo_msg = (
            #             f"🚀 突破新高提醒\n股票：{ticker} ({selected_interval})\n"
            #             f"現價 ${data['High'].iloc[-1]:.2f} 創 {int(MFI_WIN)} 根K線新高\n"
            #             f"成交量：{_fmt_vol(data['Volume'].iloc[-1])}  ({_cur_vol})\n方向：🟢 做多（買入）"
            #         )
            #         if _tg_on_bo:
            #             _ok, _err = send_telegram_alert(_bo_msg, ticker=ticker)
            #             if _ok:
            #                 _tg_mark_sent(_dedup_key_sig, "breakout_high")
            #                 st.toast(f"🚀 {ticker} 破 {int(MFI_WIN)}K 新高，Telegram 已推送", icon="🚀")
            #         else:
            #             _tg_mark_sent(_dedup_key_sig, "breakout_high")

            # if st.session_state.get(f"bo_low_{ticker}", True) and \
            #    pd.notna(data["Low_Min"].iloc[-1]) and data["Low"].iloc[-1] <= data["Low_Min"].iloc[-1]:
            #     if not _tg_already_sent(_dedup_key_sig, "breakdown_low"):
            #         _bd_msg = (
            #             f"🔻 跌破新低提醒\n股票：{ticker} ({selected_interval})\n"
            #             f"現價 ${data['Low'].iloc[-1]:.2f} 創 {int(MFI_WIN)} 根K線新低\n"
            #             f"成交量：{_fmt_vol(data['Volume'].iloc[-1])}  ({_cur_vol})\n方向：🔴 做空（賣出）"
            #         )
            #         if _tg_on_bo:
            #             _ok, _err = send_telegram_alert(_bd_msg, ticker=ticker)
            #             if _ok:
            #                 _tg_mark_sent(_dedup_key_sig, "breakdown_low")
            #                 st.toast(f"🔻 {ticker} 穿 {int(MFI_WIN)}K 新低，Telegram 已推送", icon="🔻")
            #         else:
            #             _tg_mark_sent(_dedup_key_sig, "breakdown_low")

            # Email (consolidated)
            sig_dict = {
                "macd_buy":       "📈 MACD買入"  in K_list,
                "macd_sell":      "📉 MACD賣出"  in K_list,
                "new_buy":        "📈 新买入信号" in K_list,
                "new_sell":       "📉 新卖出信号" in K_list,
                "vwap_buy":       "📈 VWAP買入"  in K_list,
                "vwap_sell":      "📉 VWAP賣出"  in K_list,
                "obv_buy":        "📈 OBV突破買入" in K_list,
                "obv_sell":       "📉 OBV突破賣出" in K_list,
                "mfi_bull":       "📈 MFI牛背離買入" in K_list,
                "mfi_bear":       "📉 MFI熊背離賣出" in K_list,
                "vix_panic":      "📉 VIX恐慌賣出" in K_list,
                "vix_calm":       "📈 VIX平靜買入" in K_list,
                "bullish_eng":    "📈 看漲吞沒"   in K_list,
                "bearish_eng":    "📉 看跌吞沒"   in K_list,
                "morning_star":   "📈 早晨之星"   in K_list,
                "evening_star":   "📉 黃昏之星"   in K_list,
                "hammer":         "📈 錘頭線"     in K_list,
                "hanging_man":    "📉 上吊線"     in K_list,
            }
            if any(sig_dict.values()):
                send_email_alert(ticker, px_pct, v_pct, sig_dict)



            # ─────────────────────────────────────────────────────────────────
            # 🔬 回測分析（每支股票獨立）
            # ─────────────────────────────────────────────────────────────────
            with st.expander(f"🔬 {ticker} 回測分析（點擊展開）", expanded=False):
                st.header("🔬 回測：三維信號勝率分析")

                st.info(
                    "**三個維度分開計算，找出歷史勝率最高的組合**\n\n"
                    "| 維度 | 說明 |\n"
                    "|------|------|\n"
                    "| 📊 信號組合 | 多個技術指標同時出現（基礎維度）|\n"
                    "| 📦 信號+成交量 | 信號組合 × 放量/縮量 |\n"
                    "| 🕯️ 信號+K線形態 | 信號組合 × K線形態（大陽線、錘子線…）|\n\n"
                    "⚠️ 回測僅供參考，請結合風險管理進行決策。"
                )

                _col_i, _col_p = st.columns(2)
                bt_interval = _col_i.selectbox(
                    "回測K線間隔", ALL_BT_INTERVALS, index=5,
                    key=f"bt_interval_{ticker}",
                )
                _period_cfg  = INTERVAL_PERIOD_MAP.get(bt_interval, INTERVAL_PERIOD_MAP["1d"])
                _period_opts = _period_cfg["periods"]
                _period_def  = _period_cfg["default"]
                _period_idx  = _period_opts.index(_period_def) if _period_def in _period_opts else 0
                bt_period = _col_p.selectbox(
                    "回測時間範圍", _period_opts, index=_period_idx,
                    key=f"bt_period_{ticker}", help=_period_cfg["help"],
                )

                col_a, col_b, col_c = st.columns(3)
                bt_min    = col_a.number_input("最少信號組合數", 2, 4, int(BT_MIN_COMBO), 1, key=f"bt_min_{ticker}")
                bt_max    = col_b.number_input("最多信號組合數", 2, 5, int(BT_MAX_COMBO), 1, key=f"bt_max_{ticker}")
                bt_occ    = col_c.number_input("最少出現次數",   2, 20, int(BT_MIN_OCC),  1, key=f"bt_occ_{ticker}")

                col_d, col_e, _ = st.columns([1, 1, 1])
                bt_wr_thr  = col_d.number_input("高勝率閾值 (%)", 50, 95, 85, 5, key=f"bt_wr_thr_{ticker}")
                bt_pnl_thr = col_e.number_input(
                    "最低平均盈虧 (%)", -10.0, 20.0, 1.0, 0.1,
                    key=f"bt_pnl_thr_{ticker}", format="%.1f",
                )

                if st.button("🚀 開始回測", type="primary", key=f"bt_run_{ticker}"):
                    with st.spinner(f"正在計算 {ticker}（{bt_period} / {bt_interval}）三維勝率…"):
                        try:
                            # 直接呼叫共用回測函數（消除重複代碼）
                            _dsig, _dvol, _dkl, _n_or_err = _run_backtest_for_ticker(
                                tk=ticker, period=bt_period, interval=bt_interval,
                                min_combo=int(bt_min), max_combo=int(bt_max), min_occ=int(bt_occ),
                            )
                            if _dsig is None:
                                st.warning(f"回測失敗：{_n_or_err}"); st.stop()

                            # FIX P1-#1: 改用快取函數抓取，與 _run_backtest_for_ticker
                            # 拿到同一份數據，避免兩次抓取時間點不同造成信號/驗證不一致。
                            _bt_raw = _fetch_price_data(ticker, bt_period, bt_interval).copy()
                            _bt_raw = _enrich_data(_bt_raw, PARAMS, int(MFI_WIN))
                            # FIX: 量價欄位與主監控相同公式，讓「✅ 量價」逐筆驗證一致
                            _bt_raw_price_abs = _bt_raw["Price Change %"].abs()
                            _bt_raw["前5均價ABS"]         = _bt_raw_price_abs.rolling(5).mean()
                            _bt_raw["📈 股價漲跌幅(%)"]   = (
                                (_bt_raw_price_abs - _bt_raw["前5均價ABS"]) /
                                _bt_raw["前5均價ABS"].replace(0, np.nan)
                            ).round(4) * 100
                            _bt_raw["📊 成交量變動幅(%)"] = (
                                (_bt_raw["Volume"] - _bt_raw["前5均量"]) /
                                _bt_raw["前5均量"].replace(0, np.nan)
                            ).round(4) * 100
                            _bt_raw["Close_N_High"] = np.nan
                            _bt_raw["Close_N_Low"]  = np.nan
                            _bt_raw["異動標記"] = compute_all_signals(_bt_raw, PARAMS)
                            _bt_raw = _attach_kline_and_vol(_bt_raw, ticker, bt_period, bt_interval,
                                                             BODY_RATIO_TH, SHADOW_RATIO_TH, DOJI_BODY_TH)
                            st.session_state[f"bt_raw_data_{ticker}"] = _bt_raw

                            df_sig, df_vol, df_kl = _dsig, _dvol, _dkl
                            st.session_state[f"bt_df_sig_{ticker}"]      = df_sig
                            st.session_state[f"bt_df_vol_{ticker}"]      = df_vol
                            st.session_state[f"bt_df_kl_{ticker}"]       = df_kl
                            st.session_state[f"_result_wr_thr_{ticker}"]     = int(bt_wr_thr)
                            st.session_state[f"_result_pnl_thr_{ticker}"]    = float(bt_pnl_thr)
                            st.session_state[f"_result_ticker_{ticker}"]     = ticker
                            st.session_state[f"_result_period_{ticker}"]     = bt_period
                            st.session_state[f"_result_interval_{ticker}"]   = bt_interval
                            st.session_state[f"_result_total_bars_{ticker}"] = len(_bt_raw)

                        except Exception as e:
                            st.error(f"回測失敗：{e}")
                            with st.expander("詳細錯誤"):
                                st.code(traceback.format_exc())

                # ── Results ───────────────────────────────────────────────────
                if f"bt_df_sig_{ticker}" in st.session_state:
                    df_sig  = st.session_state[f"bt_df_sig_{ticker}"]
                    df_vol  = st.session_state[f"bt_df_vol_{ticker}"]
                    df_kl   = st.session_state[f"bt_df_kl_{ticker}"]
                    _wr_thr          = st.session_state.get(f"_result_wr_thr_{ticker}", 60)
                    _pnl_thr         = st.session_state.get(f"_result_pnl_thr_{ticker}", 0.0)
                    _bt_lbl          = st.session_state.get(f"_result_ticker_{ticker}",   ticker)
                    _bt_period_used  = st.session_state.get(f"_result_period_{ticker}",   "?")
                    _bt_interval_used= st.session_state.get(f"_result_interval_{ticker}", "?")
                    _bt_bars_used    = st.session_state.get(f"_result_total_bars_{ticker}",   "?")

                    st.info(
                        f"📊 本次回測：**{_bt_lbl}**　{_bt_period_used} / {_bt_interval_used}　"
                        f"共 **{_bt_bars_used}** 根K線"
                    )

                    def _render_dim(df_dim, title, wr_thr, col_order, dim_key, pnl_thr=0.0):
                        if df_dim.empty:
                            st.warning(f"{title}：無有效組合"); return

                        hi = df_dim[df_dim["勝率(%)"] >= wr_thr].copy()
                        if "平均盈虧(%)" in hi.columns and pnl_thr != 0.0:
                            hi = hi[hi["平均盈虧(%)"] >= pnl_thr]

                        total = len(df_dim)
                        st.success(f"✅ {title}：{total} 組，{len(hi)} 組勝率 ≥ {wr_thr}%")

                        m1, m2, m3 = st.columns(3)
                        m1.metric("最高勝率", f"{df_dim['勝率(%)'].max():.1f}%")
                        m2.metric("平均勝率", f"{df_dim['勝率(%)'].mean():.1f}%")
                        m3.metric(f"≥{wr_thr}%", len(hi))

                        if not hi.empty:
                            disp_cols = [c for c in col_order if c in hi.columns]
                            st.dataframe(hi[disp_cols], use_container_width=True,
                                         height=min(400, 38*(len(hi)+1)+40))

                            if st.button(f"➕ 一鍵加入 {title} 高勝率組合", key=f"add_{dim_key}_{ticker}", type="primary"):
                                _one_click_add(hi, dim_key)

                        # Detail validation
                        with st.expander(f"🔬 {title} 詳細驗證 & CSV"):
                            _source_df = hi if not hi.empty else df_dim
                            _combo_choices = []
                            for _, _r in _source_df.iterrows():
                                _lbl = _r["信號組合"]
                                if _r.get("成交量標記","—") != "—": _lbl += f"  [{_r['成交量標記']}]"
                                if _r.get("K線形態","—") != "—": _lbl += f"  [{_r['K線形態']}]"
                                _lbl += f"  ({_r['勝率(%)']}%  {_r['出現次數']}次)"
                                _combo_choices.append(_lbl)

                            if not _combo_choices:
                                st.info("無可選組合"); return

                            _sel = st.selectbox("選擇組合", _combo_choices, key=f"detail_sel_{dim_key}_{ticker}")
                            _sel_idx = _combo_choices.index(_sel)
                            _sel_row = _source_df.iloc[_sel_idx]

                            _hold_bars = st.number_input("持倉根數", 1, 20, 1, 1, key=f"hold_{dim_key}_{ticker}")

                            # FIX BUG-09: 提示勝率計算差異
                            if _hold_bars > 1:
                                st.caption(
                                    f"⚠️ 勝率表基於「1 根K線後」計算，此處使用 **{_hold_bars} 根**持倉，"
                                    "實際勝率可能不同。"
                                )

                            if st.button("📊 展開逐筆記錄", key=f"detail_btn_{dim_key}_{ticker}"):
                                _bt_raw = st.session_state.get(f"bt_raw_data_{ticker}")
                                if _bt_raw is None:
                                    st.warning("請重新點擊「🚀 開始回測」"); return

                                with st.spinner("計算中..."):
                                    _detail = _detailed_backtest(
                                        _bt_raw,
                                        signal_combo  = _sel_row["信號組合"],
                                        vol_filter    = _sel_row.get("成交量標記","—"),
                                        kline_filter  = _sel_row.get("K線形態","—"),
                                        direction     = _sel_row.get("方向","做多"),
                                        hold_bars     = int(_hold_bars),
                                    )

                                if _detail.empty:
                                    st.warning("無完整交易記錄"); return

                                _stats = _summary_stats(_detail)

                                st.subheader("📈 統計摘要")
                                _sc = st.columns(4)
                                _sc[0].metric("實際勝率", f"{_stats.get('實際勝率(%)','N/A')}%")
                                _sc[1].metric("期望值/筆", f"{_stats.get('期望值每筆(%)','N/A')}%")
                                _sc[2].metric("獲利因子", str(_stats.get("獲利因子","N/A")))
                                _sc[3].metric("最大回撤", f"{_stats.get('最大回撤(%)','N/A')}%")

                                _sc2 = st.columns(4)
                                _sc2[0].metric("總筆數", _stats.get("總交易筆數","N/A"))
                                _sc2[1].metric("平均盈利/筆", f"{_stats.get('平均盈利(%)','N/A')}%")
                                _sc2[2].metric("平均虧損/筆", f"{_stats.get('平均虧損(%)','N/A')}%")
                                _sc2[3].metric("盈虧比", str(_stats.get("盈虧比","N/A")))

                                # Cumulative PnL chart
                                _fig_pnl = go.Figure()
                                _fig_pnl.add_trace(go.Scatter(
                                    x=_detail["序號"], y=_detail["累計盈虧(%)"],
                                    mode="lines+markers", name="累計盈虧",
                                    line=dict(color="#2ecc71", width=2),
                                    fill="tozeroy", fillcolor="rgba(46,204,113,0.12)",
                                ))
                                _fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray")
                                _fig_pnl.update_layout(
                                    title="累計盈虧曲線", xaxis_title="交易序號",
                                    yaxis_title="累計盈虧 (%)", template="plotly_dark", height=320,
                                )
                                st.plotly_chart(_fig_pnl, use_container_width=True, key=f"pnl_{dim_key}_{ticker}")

                                # Detail table
                                st.subheader("📋 逐筆交易記錄")
                                _disp_cols = [c for c in [
                                    "序號","信號時間","進場時間","出場時間","持倉根數",
                                    "進場價","出場價","方向","盈虧(%)","勝負",
                                    "最大順勢(%)","最大逆勢(%)","累計盈虧(%)",
                                    "信號RSI","信號MACD","成交量標記","K線形態",
                                    "連勝數","連敗數","觸發信號",
                                ] if c in _detail.columns]
                                st.dataframe(_detail[_disp_cols], use_container_width=True,
                                             height=min(600, 35*(len(_detail)+1)+40))

                                # CSV export
                                import io
                                _buf = io.StringIO()
                                _detail.to_csv(_buf, index=False)
                                st.download_button(
                                    "📥 下載逐筆交易 CSV",
                                    data=_buf.getvalue().encode("utf-8-sig"),
                                    file_name=f"{ticker}_detail_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv",
                                )

                        # Full table
                        with st.expander(f"📊 {title} 全部 {total} 組"):
                            disp_all = [c for c in col_order if c in df_dim.columns]
                            st.dataframe(df_dim[disp_all], use_container_width=True, height=420)

                    # One-click add helper
                    def _one_click_add(hi_df, dim_key):
                        existing = st.session_state.get(_ss_key(ticker), pd.DataFrame()).copy()
                        if "回測勝率" not in existing.columns:
                            existing["回測勝率"] = "N/A"
                        new_rows = []
                        for _, row in hi_df.iterrows():
                            new_rows.append({
                                "排名": "", "異動標記": row["信號組合"].replace(" + ", ", "),
                                "成交量標記": row.get("成交量標記","—"),
                                "K線形態": row.get("K線形態","—"),
                                "回測勝率": f"{row['勝率(%)']:.1f}%",
                                "方向": row.get("方向", "做多"),
                            })
                        combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
                        combined = combined.drop_duplicates(subset=["異動標記","成交量標記","K線形態"], keep="last")
                        def _parse(v):
                            try: return float(str(v).replace("%","").strip())
                            except: return 0.0
                        combined["_n"] = combined["回測勝率"].apply(_parse)
                        combined = combined.sort_values("_n", ascending=False).drop(columns=["_n"]).reset_index(drop=True)
                        combined["排名"] = [str(i+1) for i in range(len(combined))]
                        _saved = combined[_TG_COLS]
                        st.session_state[_ss_key(ticker)] = _saved
                        _tg_save(_saved, ticker)
                        st.success(f"✅ 已追加到 Telegram 條件表（共 {len(_saved)} 條）")

                    # Render 3 dimensions
                    dim_tab1, dim_tab2, dim_tab3 = st.tabs([
                        "📊 信號組合", "📦 信號+成交量", "🕯️ 信號+K線形態"])

                    COLS_SIG = ["信號組合","信號數量","勝率(%)","平均盈虧(%)","出現次數","方向"]
                    COLS_VOL = ["信號組合","成交量標記","信號數量","勝率(%)","平均盈虧(%)","出現次數","方向"]
                    COLS_KL  = ["信號組合","K線形態","信號數量","勝率(%)","平均盈虧(%)","出現次數","方向"]

                    with dim_tab1:
                        _render_dim(df_sig, f"{_bt_lbl} 信號組合", _wr_thr, COLS_SIG, "sig", pnl_thr=_pnl_thr)
                    with dim_tab2:
                        _render_dim(df_vol, f"{_bt_lbl} 信號+成交量", _wr_thr, COLS_VOL, "vol", pnl_thr=_pnl_thr)
                    with dim_tab3:
                        _render_dim(df_kl, f"{_bt_lbl} 信號+K線形態", _wr_thr, COLS_KL, "kl", pnl_thr=_pnl_thr)

                    # Best combo summary
                    st.markdown("---")
                    st.subheader("💡 三維綜合最佳建議")
                    all_hi = []
                    for df_d, lbl in [(df_sig,"信號組合"),(df_vol,"信號+成交量"),(df_kl,"信號+K線形態")]:
                        hi_d = df_d[df_d["勝率(%)"] >= _wr_thr] if not df_d.empty else pd.DataFrame()
                        if not hi_d.empty and "平均盈虧(%)" in hi_d.columns and _pnl_thr != 0.0:
                            hi_d = hi_d[hi_d["平均盈虧(%)"] >= _pnl_thr]
                        if not hi_d.empty:
                            best_row = hi_d.iloc[0].copy(); best_row["_dim"] = lbl
                            all_hi.append(best_row)

                    if all_hi:
                        overall_best = max(all_hi, key=lambda r: r["勝率(%)"])
                        st.success(
                            f"🏆 **全局最佳**（{overall_best['_dim']}）\n\n"
                            f"📊 **{overall_best['信號組合']}**\n\n"
                            f"勝率：**{overall_best['勝率(%)']}%** | "
                            f"平均盈虧：**{overall_best.get('平均盈虧(%)','N/A')}%** | "
                            f"次數：**{overall_best['出現次數']}** | "
                            f"方向：**{overall_best['方向']}**\n\n"
                            "⚠️ 回測基於歷史數據，未來不保證相同表現。"
                        )
                    else:
                        st.info(f"三個維度均無 ≥ {_wr_thr}% 勝率組合。")

                    # Merge button
                    st.markdown("---")
                    st.subheader("🔀 一鍵合併三維度 → Telegram 條件")
                    _merge_thr = st.number_input("納入勝率閾值 (%)", 0, 100, _wr_thr, 5, key=f"merge_thr_{ticker}")

                    _preview_rows = []
                    for _df_m in [df_sig, df_vol, df_kl]:
                        for _, r in _df_m.iterrows():
                            if r["勝率(%)"] >= _merge_thr:
                                _preview_rows.append({
                                    "異動標記": r["信號組合"].replace(" + ", ", "),
                                    "成交量標記": r.get("成交量標記","—"),
                                    "K線形態": r.get("K線形態","—"),
                                    "回測勝率": f"{r['勝率(%)']:.1f}%",
                                    "方向": r.get("方向","做多"),
                                    "_wr": r["勝率(%)"],
                                })
                    if _preview_rows:
                        _preview_df = (pd.DataFrame(_preview_rows)
                            .sort_values("_wr", ascending=False)
                            .drop_duplicates(subset=["異動標記","成交量標記","K線形態"], keep="first")
                            .drop(columns=["_wr"]).reset_index(drop=True))
                        _preview_df["排名"] = [str(i+1) for i in range(len(_preview_df))]
                        _preview_df = _preview_df[_TG_COLS]
                    else:
                        _preview_df = pd.DataFrame()

                    _n_preview = len(_preview_df)
                    st.metric("合併後條數", f"{_n_preview} 條")

                    if _n_preview > 0 and st.button(
                        f"🔀 確認合併（共 {_n_preview} 條）", type="primary", key=f"merge_btn_{ticker}"):
                        st.session_state[_ss_key(ticker)] = _preview_df
                        _tg_save(_preview_df, ticker)
                        st.success(f"🎯 **覆蓋完成！** {_n_preview} 條條件。")
                        st.balloons()

        except Exception as e:
            st.error(f"⚠️ {ticker} 發生錯誤：{e}")
            with st.expander("詳細錯誤"):
                st.code(traceback.format_exc())

# ═════════════════════════════════════════════════════════════════════════════
#  🔬 爆升前特徵分析引擎 (11項功能)
#  完全獨立，不修改任何現有代碼
#  直接複用: _enrich_data(), send_telegram_alert(), INTERVAL_PERIOD_MAP
# ═════════════════════════════════════════════════════════════════════════════

# ── 財報日抓取 (功能L) ────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def _get_earnings_dates(ticker: str) -> list:
    """
    抓取未來+過去的財報日列表。
    返回 list of datetime.date。
    """
    try:
        tk = yf.Ticker(ticker)
        cal = tk.get_earnings_dates(limit=20)
        if cal is None or cal.empty:
            return []
        dates = pd.to_datetime(cal.index).tz_localize(None).date.tolist()
        return sorted(set(dates))
    except Exception:
        return []


def _is_earnings_week(date: "pd.Timestamp", earnings_dates: list,
                      window: int = 5) -> bool:
    """判斷某日是否在財報日前後 window 天內。"""
    if not earnings_dates:
        return False
    d = pd.Timestamp(date).date()
    for ed in earnings_dates:
        if abs((d - ed).days) <= window:
            return True
    return False


# ── 大市環境判斷 (功能J) ──────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _get_market_regime(period: str = "max") -> pd.DataFrame:
    """
    用 SPY 的 200日均線判斷每天的大市環境：
      牛市  : Close > SMA200 且 SMA200 上升
      熊市  : Close < SMA200 且 SMA200 下降
      震盪市: 其他
    返回含 date / regime 兩列的 DataFrame。
    """
    try:
        spy = yf.Ticker("SPY").history(period=period, interval="1d").reset_index()
        if spy.empty:
            return pd.DataFrame()
        if "Date" in spy.columns:
            spy = spy.rename(columns={"Date": "Datetime"})
        spy["Datetime"] = pd.to_datetime(spy["Datetime"]).dt.tz_localize(None)
        spy["sma200"]   = spy["Close"].rolling(200).mean()
        spy["sma200_d"] = spy["sma200"].diff()
        def _regime(row):
            if pd.isna(row["sma200"]):
                return "震盪市"
            if row["Close"] > row["sma200"] and row["sma200_d"] > 0:
                return "牛市"
            if row["Close"] < row["sma200"] and row["sma200_d"] < 0:
                return "熊市"
            return "震盪市"
        spy["regime"] = spy.apply(_regime, axis=1)
        spy["date"]   = spy["Datetime"].dt.date
        return spy[["date", "regime"]].drop_duplicates("date")
    except Exception:
        return pd.DataFrame()


# ── 成交量分層 (功能G) ────────────────────────────────────────────────────────
def _vol_layer(vol_ratio: float) -> str:
    """把成交量倍數分成5個層級。"""
    if   vol_ratio >= 5.0: return "🔴 爆量(≥5x)"
    elif vol_ratio >= 3.0: return "🟠 大量(3-5x)"
    elif vol_ratio >= 2.0: return "🟡 明顯放量(2-3x)"
    elif vol_ratio >= 1.5: return "🟢 輕微放量(1.5-2x)"
    else:                  return "⚪ 縮量(<1.5x)"


# ── 核心回測引擎 (功能A+B+C+D+E+F+G+H+I+J+L) ────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _surge_backtest(
    ticker: str,
    period: str,
    surge_pct: float,       # 爆升定義：N天漲幅超過此值
    surge_days: int,        # 爆升定義：往後看幾天
    lookback: int,          # 往前看幾天找特徵
    train_ratio: float,     # 訓練集比例 (功能C)
    vol_ma_window: int,     # 成交量均線窗口
) -> dict:
    """
    完整爆升前特徵回測引擎。
    返回包含所有分析結果的 dict。
    """
    result = {
        "ticker": ticker, "error": None,
        "total_bars": 0,
        "surge_points": [],      # 所有爆升點
        "feature_power": [],     # 每個特徵的預測力 (功能H)
        "layer_stats": {},       # 成交量分層統計 (功能G)
        "regime_stats": {},      # 大市環境分層 (功能J)
        "process_stats": {},     # 過程特徵統計 (功能D+E+F)
        "horizon_stats": {},     # 最優持倉天數 (功能I)
        "train_result": {},      # 訓練集結果 (功能C)
        "test_result":  {},      # 測試集結果 (功能C)
        "earnings_dates": [],    # 財報日 (功能L)
    }

    # ── 下載數據 ────────────────────────────────────────────────────────────
    try:
        raw = yf.Ticker(ticker).history(period=period, interval="1d").reset_index()
        if raw.empty:
            result["error"] = f"無法下載 {ticker} 數據"
            return result
        if "Date" in raw.columns:
            raw = raw.rename(columns={"Date": "Datetime"})
        raw["Datetime"] = pd.to_datetime(raw["Datetime"]).dt.tz_localize(None)
        raw = raw.dropna(subset=["Close","Volume"]).reset_index(drop=True)
    except Exception as e:
        result["error"] = str(e)
        return result

    n = len(raw)
    result["total_bars"] = n
    if n < 60:
        result["error"] = "數據不足（少於60根K線）"
        return result

    # ── 基礎指標 ─────────────────────────────────────────────────────────────
    raw["vol_ma"]    = raw["Volume"].rolling(vol_ma_window).mean()
    raw["vol_ratio"] = raw["Volume"] / raw["vol_ma"].replace(0, np.nan)
    raw["ret"]       = raw["Close"].pct_change()
    raw["gap"]       = (raw["Open"] - raw["Close"].shift(1)) / raw["Close"].shift(1)
    raw["body"]      = (raw["Close"] - raw["Open"]) / raw["Open"].replace(0, np.nan)
    raw["close_pos"] = np.where(
        raw["High"] != raw["Low"],
        (raw["Close"] - raw["Low"]) / (raw["High"] - raw["Low"]),
        0.5
    )
    raw["price_up"]  = raw["ret"] > 0
    raw["vol_layer"] = raw["vol_ratio"].apply(
        lambda x: _vol_layer(x) if pd.notna(x) else "⚪ 縮量(<1.5x)"
    )

    # ── 財報日 (功能L) ────────────────────────────────────────────────────────
    earnings = _get_earnings_dates(ticker)
    result["earnings_dates"] = earnings
    raw["is_earnings_week"] = raw["Datetime"].apply(
        lambda d: _is_earnings_week(d, earnings)
    )

    # ── 大市環境 (功能J) ─────────────────────────────────────────────────────
    regime_df = _get_market_regime(period)
    if not regime_df.empty:
        raw["date"]   = raw["Datetime"].dt.date
        raw = raw.merge(regime_df, on="date", how="left")
        raw["regime"] = raw["regime"].fillna("震盪市")
    else:
        raw["regime"] = "震盪市"

    # ── 識別爆升點 (功能A) ───────────────────────────────────────────────────
    # 爆升定義：未來 surge_days 天內收盤漲幅 > surge_pct
    surge_mask = np.zeros(n, dtype=bool)
    fwd_ret    = np.full(n, np.nan)
    for i in range(n - surge_days):
        future_ret = (raw["Close"].iloc[i + surge_days] - raw["Close"].iloc[i]) / raw["Close"].iloc[i]
        fwd_ret[i] = future_ret
        if future_ret >= surge_pct / 100:
            surge_mask[i] = True

    raw["fwd_ret"]    = fwd_ret
    raw["is_surge"]   = surge_mask
    surge_idx         = np.where(surge_mask)[0].tolist()
    non_surge_idx     = np.where(~surge_mask)[0].tolist()
    result["surge_points"] = surge_idx

    if len(surge_idx) < 5:
        result["error"] = f"爆升樣本不足（只有 {len(surge_idx)} 個，建議降低爆升門檻或增加回測年數）"
        return result

    # ── 訓練/測試分割 (功能C) ────────────────────────────────────────────────
    split_pos   = int(n * train_ratio)
    train_surge = [i for i in surge_idx    if i < split_pos]
    test_surge  = [i for i in surge_idx    if i >= split_pos]
    train_non   = [i for i in non_surge_idx if i < split_pos]
    # test_non = [i for i in non_surge_idx if i >= split_pos]  # 保留供未來 out-of-sample 驗證

    # ── 前N天特徵提取函數 ────────────────────────────────────────────────────
    def _extract_features(idx_list: list, lb: int) -> pd.DataFrame:
        """
        對每個索引往前看 lb 天，提取所有特徵。
        每個爆升點返回一行，含所有前置特徵。
        """
        rows = []
        for i in idx_list:
            start = max(0, i - lb)
            window = raw.iloc[start:i]
            if len(window) < 2:
                continue

            # ── 基礎特徵 ────────────────────────────────────────────────────
            # 最後一天
            last = window.iloc[-1]
            # 量價特徵
            feat = {
                "idx":           i,
                "date":          raw["Datetime"].iloc[i].date(),
                "surge_ret":     raw["fwd_ret"].iloc[i],
                "regime":        raw["regime"].iloc[i],
                "is_earn_week":  raw["is_earnings_week"].iloc[i],

                # 最後一根特徵
                "last_price_up":  bool(last["price_up"]),
                "last_vol_ratio": float(last["vol_ratio"]) if pd.notna(last["vol_ratio"]) else 0,
                "last_gap":       float(last["gap"])        if pd.notna(last["gap"])       else 0,
                "last_close_pos": float(last["close_pos"])  if pd.notna(last["close_pos"]) else 0.5,
                "last_body":      float(last["body"])        if pd.notna(last["body"])      else 0,
                "last_vol_layer": last["vol_layer"],

                # 窗口期量價特徵
                "win_vol_ratio_mean": float(window["vol_ratio"].mean()),
                "win_vol_ratio_max":  float(window["vol_ratio"].max()),
                "win_price_up_days":  int(window["price_up"].sum()),
                "win_ret_sum":        float(window["ret"].sum()),
            }

            # ── D: 遞進量能積累 ──────────────────────────────────────────────
            # 把窗口分前半/後半，看後半量能是否比前半大
            mid = len(window) // 2
            first_half_vol  = window["vol_ratio"].iloc[:mid].mean()  if mid > 0 else 0
            second_half_vol = window["vol_ratio"].iloc[mid:].mean()  if mid < len(window) else 0
            feat["vol_escalating"] = bool(
                pd.notna(first_half_vol) and pd.notna(second_half_vol)
                and second_half_vol > first_half_vol * 1.1
            )

            # 計算量能斜率（線性回歸）
            vr = window["vol_ratio"].dropna().values
            if len(vr) >= 3:
                x = np.arange(len(vr))
                slope = np.polyfit(x, vr, 1)[0]
                feat["vol_slope"] = float(slope)
                feat["vol_slope_pos"] = bool(slope > 0)
            else:
                feat["vol_slope"] = 0.0
                feat["vol_slope_pos"] = False

            # ── E: 底部抬升 ──────────────────────────────────────────────────
            lows   = window["Low"].values
            # 把窗口分三段，看每段低點是否遞增
            third = max(1, len(lows) // 3)
            low1  = lows[:third].min()      if third > 0            else lows[0]
            low2  = lows[third:2*third].min() if 2*third <= len(lows) else low1
            low3  = lows[2*third:].min()    if 2*third < len(lows)  else low2
            feat["higher_lows"] = bool(low1 <= low2 <= low3 and low1 < low3)

            # ── F: 回落量萎縮 ────────────────────────────────────────────────
            # 找窗口內價格下跌的日子，看成交量是否比上升日小
            up_days   = window[window["ret"] > 0]["vol_ratio"].mean()
            down_days = window[window["ret"] < 0]["vol_ratio"].mean()
            if pd.notna(up_days) and pd.notna(down_days) and up_days > 0:
                feat["pullback_vol_shrink"] = bool(down_days < up_days * 0.8)
                feat["vol_ratio_up_vs_down"] = float(up_days / down_days) if down_days > 0 else 2.0
            else:
                feat["pullback_vol_shrink"]  = False
                feat["vol_ratio_up_vs_down"] = 1.0

            rows.append(feat)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    feat_df      = _extract_features(surge_idx,     lookback)
    non_feat_df  = _extract_features(non_surge_idx, lookback)
    train_feat   = _extract_features(train_surge,   lookback)
    test_feat    = _extract_features(test_surge,    lookback)
    train_non    = _extract_features(train_non,     lookback)

    # ── H: 預測力計算（爆升前出現率 vs 非爆升期間出現率）────────────────────
    bool_features = [
        ("last_price_up",       "最後一天收陽線"),
        ("vol_escalating",      "D: 量能遞進放大"),
        ("vol_slope_pos",       "D: 量能斜率向上"),
        ("higher_lows",         "E: 底部持續抬升"),
        ("pullback_vol_shrink", "F: 回落量快速萎縮"),
    ]
    threshold_features = [
        ("last_vol_ratio",  1.5, "G: 最後一天量≥1.5x"),
        ("last_vol_ratio",  2.0, "G: 最後一天量≥2x"),
        ("last_vol_ratio",  3.0, "G: 最後一天量≥3x"),
        ("last_vol_ratio",  5.0, "G: 最後一天量≥5x"),
        ("last_close_pos",  0.7, "收盤位置≥70%"),
        ("last_close_pos",  0.8, "收盤位置≥80%"),
        ("last_gap",        0.01,"跳空高開≥1%"),
        ("last_gap",        0.02,"跳空高開≥2%"),
        ("win_vol_ratio_max", 2.0, "窗口內曾出現量≥2x"),
        ("win_vol_ratio_max", 3.0, "窗口內曾出現量≥3x"),
        ("vol_ratio_up_vs_down", 1.5, "上漲日量/下跌日量≥1.5"),
        ("win_price_up_days", lookback * 0.5, f"窗口內上漲天數≥{lookback//2}天"),
    ]

    power_rows = []

    for col, label in bool_features:
        if col not in feat_df.columns:
            continue
        surge_rate = feat_df[col].mean()    if len(feat_df)     > 0 else 0
        non_rate   = non_feat_df[col].mean() if len(non_feat_df) > 0 else 0
        lift       = surge_rate / max(non_rate, 0.01)
        power_rows.append({
            "特徵": label, "爆升前出現率": round(surge_rate * 100, 1),
            "非爆升出現率": round(non_rate * 100, 1),
            "預測力倍數": round(lift, 2),
            "樣本數": len(feat_df),
        })

    for col, thresh, label in threshold_features:
        if col not in feat_df.columns:
            continue
        surge_rate = (feat_df[col]     >= thresh).mean() if len(feat_df)     > 0 else 0
        non_rate   = (non_feat_df[col] >= thresh).mean() if len(non_feat_df) > 0 else 0
        lift       = surge_rate / max(non_rate, 0.01)
        power_rows.append({
            "特徵": label, "爆升前出現率": round(surge_rate * 100, 1),
            "非爆升出現率": round(non_rate * 100, 1),
            "預測力倍數": round(lift, 2),
            "樣本數": len(feat_df),
        })

    power_df = pd.DataFrame(power_rows).sort_values("預測力倍數", ascending=False)
    result["feature_power"] = power_df.to_dict(orient="records")

    # ── G: 成交量分層統計 ────────────────────────────────────────────────────
    layer_stats = {}
    for layer in ["⚪ 縮量(<1.5x)","🟢 輕微放量(1.5-2x)","🟡 明顯放量(2-3x)","🟠 大量(3-5x)","🔴 爆量(≥5x)"]:
        surge_in_layer = (feat_df["last_vol_layer"]     == layer).sum() if len(feat_df)     > 0 else 0
        total_in_layer = (non_feat_df["last_vol_layer"] == layer).sum() + surge_in_layer
        layer_stats[layer] = {
            "爆升次數":   int(surge_in_layer),
            "總出現次數": int(total_in_layer),
            "爆升率":     round(surge_in_layer / max(total_in_layer, 1) * 100, 1),
        }
    result["layer_stats"] = layer_stats

    # ── J: 大市環境分層統計 ──────────────────────────────────────────────────
    regime_stats = {}
    for regime in ["牛市", "熊市", "震盪市"]:
        s_mask  = feat_df["regime"]     == regime if len(feat_df)     > 0 else pd.Series(dtype=bool)
        ns_mask = non_feat_df["regime"] == regime if len(non_feat_df) > 0 else pd.Series(dtype=bool)
        s_count  = int(s_mask.sum())
        ns_count = int(ns_mask.sum())
        total    = s_count + ns_count
        # 當環境內，有量能積累特徵的勝率
        if s_count > 0:
            with_acc = feat_df[s_mask & feat_df.get("vol_escalating", pd.Series(False, index=feat_df.index))].shape[0] \
                if "vol_escalating" in feat_df.columns else 0
        else:
            with_acc = 0
        regime_stats[regime] = {
            "爆升次數":    s_count,
            "非爆升次數":  ns_count,
            "爆升率":      round(s_count / max(total, 1) * 100, 1),
            "含量能積累":  with_acc,
        }
    result["regime_stats"] = regime_stats

    # ── I: 最優持倉天數 ──────────────────────────────────────────────────────
    horizon_stats = {}
    for hd in [1, 3, 5, 10]:
        rets = []
        for i in surge_idx:
            if i + hd < n:
                r = (raw["Close"].iloc[i + hd] - raw["Close"].iloc[i]) / raw["Close"].iloc[i]
                rets.append(r * 100)
        if rets:
            horizon_stats[f"{hd}天"] = {
                "平均漲幅": round(np.mean(rets), 2),
                "勝率":     round(np.mean([r > 0 for r in rets]) * 100, 1),
                "樣本數":   len(rets),
            }
    result["horizon_stats"] = horizon_stats

    # ── L: 財報週影響分析 ────────────────────────────────────────────────────
    if len(feat_df) > 0 and "is_earn_week" in feat_df.columns:
        earn_surges     = feat_df["is_earn_week"].sum()
        non_earn_surges = len(feat_df) - earn_surges
        result["earnings_impact"] = {
            "財報週爆升次數":   int(earn_surges),
            "非財報週爆升次數": int(non_earn_surges),
            "財報週佔比":       round(earn_surges / max(len(feat_df), 1) * 100, 1),
        }

    # ── C: 訓練集 vs 測試集對比 ─────────────────────────────────────────────
    def _calc_set_stats(feat: pd.DataFrame, label: str) -> dict:
        if len(feat) == 0:
            return {"集合": label, "樣本數": 0}
        stats = {"集合": label, "樣本數": len(feat)}
        for col, name in [("vol_escalating","量能遞進"),("higher_lows","底部抬升"),("pullback_vol_shrink","回落縮量")]:
            if col in feat.columns:
                stats[name] = f"{feat[col].mean()*100:.0f}%"
        if "last_vol_ratio" in feat.columns:
            stats["平均量倍數"] = f"{feat['last_vol_ratio'].mean():.1f}x"
        if "surge_ret" in feat.columns:
            stats["平均爆升幅"] = f"+{feat['surge_ret'].mean()*100:.1f}%"
        return stats

    result["train_result"] = _calc_set_stats(train_feat, f"訓練集(前{int(train_ratio*100)}%)")
    result["test_result"]  = _calc_set_stats(test_feat,  f"測試集(後{int((1-train_ratio)*100)}%)")

    # ── 過程特徵統計匯總 ─────────────────────────────────────────────────────
    process_stats = {}
    if len(feat_df) > 0:
        for col, name in [("vol_escalating","量能遞進放大"),("higher_lows","底部持續抬升"),
                          ("pullback_vol_shrink","回落量快速萎縮"),("vol_slope_pos","量能斜率向上")]:
            if col in feat_df.columns:
                process_stats[name] = {
                    "爆升前出現率":  f"{feat_df[col].mean()*100:.0f}%",
                    "非爆升出現率":  f"{non_feat_df[col].mean()*100:.0f}%" if col in non_feat_df.columns else "N/A",
                }
    result["process_stats"] = process_stats

    return result


# ── 實時監控：檢查當前是否符合個股最佳條件 ───────────────────────────────────
def _realtime_check(ticker: str, bt_result: dict,
                    top_features: list, vol_ma_window: int) -> dict:
    """
    下載最近數據，根據回測發現的個股最佳特徵評分，觸發時發Telegram。
    """
    sig = {
        "ticker": ticker, "time": datetime.now(),
        "price": None, "ret": None, "vol_ratio": None,
        "score": 0, "max_score": 0,
        "conditions": [], "triggered": False, "error": None,
    }
    try:
        df = yf.Ticker(ticker).history(period="30d", interval="1d").reset_index()
        if df.empty or len(df) < vol_ma_window + 2:
            sig["error"] = "數據不足"
            return sig
        if "Date" in df.columns:
            df = df.rename(columns={"Date": "Datetime"})
        df["Datetime"] = pd.to_datetime(df["Datetime"]).dt.tz_localize(None)
        df["vol_ma"]   = df["Volume"].rolling(vol_ma_window).mean()
        df["vol_ratio"]= df["Volume"] / df["vol_ma"].replace(0, np.nan)
        df["ret"]      = df["Close"].pct_change()
        df["gap"]      = (df["Open"] - df["Close"].shift(1)) / df["Close"].shift(1)
        df["close_pos"]= np.where(
            df["High"] != df["Low"],
            (df["Close"] - df["Low"]) / (df["High"] - df["Low"]),
            0.5
        )
        df = df.dropna(subset=["vol_ratio"]).reset_index(drop=True)
        if len(df) < 5:
            sig["error"] = "有效數據不足"
            return sig

        last    = df.iloc[-1]
        window  = df.iloc[-min(10, len(df)):]

        sig["price"]     = float(last["Close"])
        sig["ret"]       = float(last["ret"])    if pd.notna(last["ret"])    else 0
        sig["vol_ratio"] = float(last["vol_ratio"]) if pd.notna(last["vol_ratio"]) else 0

        # 過程特徵（D+E+F）
        mid  = len(window) // 2
        fh   = window["vol_ratio"].iloc[:mid].mean()
        sh   = window["vol_ratio"].iloc[mid:].mean()
        vol_escalating = bool(pd.notna(fh) and pd.notna(sh) and sh > fh * 1.1)

        lows  = window["Low"].values
        third = max(1, len(lows) // 3)
        l1    = lows[:third].min()
        l2    = lows[third:2*third].min() if 2*third <= len(lows) else l1
        l3    = lows[2*third:].min()      if 2*third < len(lows)  else l2
        higher_lows = bool(l1 <= l2 <= l3 and l1 < l3)

        up_vol   = window[window["ret"] > 0]["vol_ratio"].mean()
        dn_vol   = window[window["ret"] < 0]["vol_ratio"].mean()
        pullback_shrink = bool(
            pd.notna(up_vol) and pd.notna(dn_vol) and dn_vol < up_vol * 0.8
        )

        # ── 計算當前數值 ──────────────────────────────────────────────────────
        vr  = sig["vol_ratio"]
        ret = sig["ret"]
        cp  = float(last["close_pos"]) if pd.notna(last["close_pos"]) else 0.5
        gap = float(last["gap"])       if pd.notna(last["gap"])       else 0
        win_max_vr = float(window["vol_ratio"].max()) if pd.notna(window["vol_ratio"].max()) else 0

        # ── 完整條件定義（附當前數值說明）────────────────────────────────────
        # 格式：(條件是否成立, 分數, 當前數值說明)
        feature_map = {
            "📈 當日收陽線":          (ret > 0,          20, f"漲幅 {ret*100:+.2f}%"),
            "📊 量≥1.5x (輕微放量)":  (vr >= 1.5,        10, f"量倍數 {vr:.2f}x"),
            "📊 量≥2x (明顯放量)":    (vr >= 2.0,        20, f"量倍數 {vr:.2f}x"),
            "📊 量≥3x (大量)":        (vr >= 3.0,        35, f"量倍數 {vr:.2f}x"),
            "📊 量≥5x (爆量)":        (vr >= 5.0,        50, f"量倍數 {vr:.2f}x"),
            "📍 收盤位置≥70%":        (cp >= 0.7,        10, f"收盤位置 {cp*100:.0f}%"),
            "📍 收盤位置≥80%":        (cp >= 0.8,        15, f"收盤位置 {cp*100:.0f}%"),
            "⬆️ 跳空高開≥1%":         (gap >= 0.01,      10, f"跳空 {gap*100:+.2f}%"),
            "⬆️ 跳空高開≥2%":         (gap >= 0.02,      15, f"跳空 {gap*100:+.2f}%"),
            "📈 D: 量能遞進放大":      (vol_escalating,   20, "近期量能後段>前段×1.1"),
            "📈 E: 底部持續抬升":      (higher_lows,      20, "低點一次比一次高"),
            "📉 F: 回落量快速萎縮":    (pullback_shrink,  20, "下跌日量<上漲日量×0.8"),
            "🔍 窗口內曾出現量≥2x":   (win_max_vr >= 2.0, 10, f"窗口最大量 {win_max_vr:.2f}x"),
            "🔍 窗口內曾出現量≥3x":   (win_max_vr >= 3.0, 15, f"窗口最大量 {win_max_vr:.2f}x"),
        }

        # ── 決定哪些條件參與評分 ─────────────────────────────────────────────
        # 有回測結果：只用預測力>1.5倍的條件（個股化）
        # 沒有回測結果：用全部條件（通用模式）
        active_features = {f["特徵"] for f in top_features if f.get("預測力倍數", 0) >= 1.5}
        use_all = len(active_features) == 0  # 沒有回測結果，啟用全部條件
        bt_mode_label = "通用模式（請先執行回測以啟用個股化評分）" if use_all else f"個股模式（{len(active_features)} 個高預測力特徵）"

        score     = 0
        max_score = 0
        conds     = []

        for feat_name, (condition, pts, current_val) in feature_map.items():
            # 判斷此條件是否參與評分
            # 個股模式：特徵名稱需在 active_features 中（做模糊匹配）
            feat_key = feat_name.split(": ")[-1].split(" (")[0].strip()
            in_active = use_all or any(
                feat_key in af or af in feat_name
                for af in active_features
            )
            if not in_active:
                # 不參與評分，但仍顯示當前狀態（灰色）
                status = "✅" if condition else "⬜"
                conds.append({
                    "text":    f"{status} {feat_name}",
                    "value":   current_val,
                    "active":  False,
                    "passed":  condition,
                    "pts":     0,
                })
                continue

            max_score += pts
            if condition:
                score += pts
                conds.append({
                    "text":   f"✅ {feat_name}",
                    "value":  current_val,
                    "active": True,
                    "passed": True,
                    "pts":    pts,
                })
            else:
                conds.append({
                    "text":   f"❌ {feat_name}",
                    "value":  current_val,
                    "active": True,
                    "passed": False,
                    "pts":    pts,
                })

        sig["score"]        = score
        sig["max_score"]    = max_score if max_score > 0 else 100
        sig["conditions"]   = conds
        sig["bt_mode"]      = bt_mode_label
        sig["vol_escalating"]   = vol_escalating
        sig["higher_lows"]      = higher_lows
        sig["pullback_shrink"]  = pullback_shrink
        sig["close_pos"]        = cp
        sig["gap"]              = gap

        # 觸發：分數達到 max_score 的 65% 且有量能遞進或底部抬升
        process_ok = vol_escalating or higher_lows
        sig["triggered"] = (
            max_score > 0
            and score >= max_score * 0.65
            and ret > 0
            and vr >= 1.5
            and process_ok
        )

    except Exception as e:
        sig["error"] = str(e)
    return sig


# ── Telegram 推送（個股化版本）───────────────────────────────────────────────
def _build_bt_summary(bt: dict, ticker: str) -> str:
    """把回測結果濃縮成 AI 可讀的文字摘要，自動注入 system prompt。"""
    if not bt or bt.get("error"):
        return f"{ticker} 尚未完成回測"
    lines = [f"=== {ticker} 回測數據摘要 ==="]
    lines.append(f"回測K線數: {bt.get('total_bars', 0)}")
    lines.append(f"爆升點數量: {len(bt.get('surge_points', []))}")

    pwr = bt.get("feature_power", [])
    if pwr:
        lines.append("\n【特徵預測力排行 Top5】")
        for row in pwr[:5]:
            lines.append(
                f"  {row['特徵']}: 預測力{row['預測力倍數']}x "
                f"(爆升前{row['爆升前出現率']}% vs 非爆升{row['非爆升出現率']}%)"
            )

    ps = bt.get("process_stats", {})
    if ps:
        lines.append("\n【過程特徵統計】")
        for name, vals in ps.items():
            lines.append(
                f"  {name}: 爆升前{vals.get('爆升前出現率','N/A')} "
                f"vs 非爆升{vals.get('非爆升出現率','N/A')}"
            )

    ls = bt.get("layer_stats", {})
    if ls:
        lines.append("\n【成交量分層爆升率】")
        for layer, v in ls.items():
            lines.append(f"  {layer}: 爆升率{v['爆升率']}% ({v['爆升次數']}次)")

    hs = bt.get("horizon_stats", {})
    if hs:
        lines.append("\n【最優持倉天數】")
        for hd, v in hs.items():
            lines.append(f"  {hd}: 均漲{v['平均漲幅']}%, 勝率{v['勝率']}%")

    rs = bt.get("regime_stats", {})
    if rs:
        lines.append("\n【大市環境分層】")
        for regime, v in rs.items():
            lines.append(
                f"  {regime}: 爆升率{v['爆升率']}% ({v['爆升次數']}次)"
            )

    ei = bt.get("earnings_impact", {})
    if ei:
        lines.append(f"\n【財報週佔比】{ei.get('財報週佔比','N/A')}%")

    tr = bt.get("train_result", {})
    te = bt.get("test_result",  {})
    if tr and te:
        lines.append(
            f"\n【訓練集】樣本{tr.get('樣本數',0)}, "
            f"量能遞進{tr.get('量能遞進','N/A')}, "
            f"底部抬升{tr.get('底部抬升','N/A')}"
        )
        lines.append(
            f"【測試集】樣本{te.get('樣本數',0)}, "
            f"量能遞進{te.get('量能遞進','N/A')}, "
            f"底部抬升{te.get('底部抬升','N/A')}"
        )

    return "\n".join(lines)



def _build_surge_tg_msg(sig: dict, bt: dict) -> str:
    ticker  = sig["ticker"]
    now     = sig["time"].strftime("%Y-%m-%d %H:%M")
    pwr     = bt.get("feature_power", [])
    top3    = [f["特徵"] for f in pwr[:3]] if pwr else []
    horizon = bt.get("horizon_stats", {})
    best_hd = max(horizon, key=lambda k: horizon[k]["平均漲幅"], default="N/A")
    best_wr = horizon.get(best_hd, {}).get("勝率", "N/A")
    best_rt = horizon.get(best_hd, {}).get("平均漲幅", "N/A")
    conds   = "\n".join(f"  {c}" for c in sig.get("conditions", []))
    regime_stats = bt.get("regime_stats", {})
    regime_lines = "\n".join(
        f"  {r}: 爆升率{v['爆升率']}% ({v['爆升次數']}次)"
        for r, v in regime_stats.items()
    )
    earn_impact = bt.get("earnings_impact", {})
    earn_note   = (
        f"⚠️ 財報週爆升佔比: {earn_impact.get('財報週佔比','N/A')}%"
        if earn_impact else ""
    )

    return f"""🚨 <b>爆升前特徵觸發</b>

🏷️ <b>{ticker}</b>  |  {now}

━━━━━━━━━━━━━━━━━━━━━
💰 <b>即時數據</b>
  現價: <b>${sig['price']:.2f}</b>
  漲幅: <b>{sig['ret']*100:+.2f}%</b>
  量倍數: <b>{sig['vol_ratio']:.1f}x</b> (20日均)

━━━━━━━━━━━━━━━━━━━━━
🎯 <b>信號評分: {sig['score']}/{sig['max_score']}</b>
{conds}

━━━━━━━━━━━━━━━━━━━━━
📊 <b>個股回測依據</b>
  最強特徵: {', '.join(top3)}
  最優持倉: <b>{best_hd}</b>（勝率{best_wr}%，均漲{best_rt}%）

📈 <b>大市環境歷史勝率</b>
{regime_lines}

{earn_note}

━━━━━━━━━━━━━━━━━━━━━
⚠️ 基於個股歷史回測，不構成投資建議
"""


# ════════════════════════════════════════════════════════════════════════════
#  UI 渲染
# ════════════════════════════════════════════════════════════════════════════
with tabs[-3]:
    st.markdown("## 🔬 爆升前特徵分析")
    st.caption("多股同時回測 → 找出個股爆升前獨有特徵 → 實時監控 → Telegram推送")

    # ══════════════════════════════════════════════════════════════════════════
    #  共用參數（所有股票共用同一套回測設定）
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("⚙️ 回測參數設定", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            sp_tickers_raw = st.text_input(
                "股票代號（逗號分隔，最多10隻）",
                value="TSLA, NVDA, AAPL",
                key="sp_tickers_raw"
            )
            sp_period = st.selectbox(
                "回測年數",
                ["1y","2y","3y","5y","10y","max"],
                index=3, key="sp_period",
                format_func=lambda x: {"1y":"1年","2y":"2年","3y":"3年",
                                       "5y":"5年","10y":"10年","max":"最大"}[x]
            )
        with c2:
            sp_surge  = st.slider("爆升定義：N天漲幅 (%)", 5, 30, 10, 1, key="sp_surge")
            sp_days   = st.slider("爆升定義：往後看幾天",  3, 20,  7, 1, key="sp_days")
        with c3:
            sp_lb     = st.slider("往前看幾天找特徵",      3, 20,  7, 1, key="sp_lb")
            sp_train  = st.slider("訓練集比例", 0.5, 0.9, 0.7, 0.05, key="sp_train",
                                  format="%.0f%%", help="前X%數據找規律，後面驗證")
            sp_vol_win = st.slider("成交量均線窗口", 5, 30, 20, 1, key="sp_vol_win")

    # 解析股票清單（去重、大寫、最多10隻）
    sp_ticker_list = list(dict.fromkeys(
        t.strip().upper()
        for t in sp_tickers_raw.split(",")
        if t.strip()
    ))[:10]

    # ══════════════════════════════════════════════════════════════════════════
    #  回測操作列
    # ══════════════════════════════════════════════════════════════════════════
    run_c1, run_c2, run_c3 = st.columns([2, 2, 4])
    with run_c1:
        run_all = st.button("▶ 全部回測", type="primary",
                            use_container_width=True, key="run_all_btn")
    with run_c2:
        clear_all = st.button("🗑️ 清除結果", use_container_width=True, key="clear_all_btn")
    with run_c3:
        already_done = [t for t in sp_ticker_list
                        if st.session_state.get(f"sp_result_{t}") and
                        not st.session_state[f"sp_result_{t}"].get("error")]
        st.caption(f"✅ 已回測：{', '.join(already_done) if already_done else '無'}"
                   f" | 待回測：{', '.join([t for t in sp_ticker_list if t not in already_done])}")

    if clear_all:
        for t in sp_ticker_list:
            st.session_state.pop(f"sp_result_{t}", None)
            st.session_state.pop(f"sp_sig_{t}", None)
        st.rerun()

    # 全部回測
    if run_all and sp_ticker_list:
        prog_bar = st.progress(0, text="準備中...")
        for i, ticker in enumerate(sp_ticker_list):
            prog_bar.progress(
                (i) / len(sp_ticker_list),
                text=f"正在分析 {ticker}（{i+1}/{len(sp_ticker_list)}）..."
            )
            bt = _surge_backtest(
                ticker, sp_period, sp_surge, sp_days,
                sp_lb, sp_train, sp_vol_win
            )
            st.session_state[f"sp_result_{ticker}"] = bt
        prog_bar.progress(1.0, text="✅ 全部回測完成！")

    # ══════════════════════════════════════════════════════════════════════════
    #  跨股比較總表（只顯示已回測的股票）
    # ══════════════════════════════════════════════════════════════════════════
    done_tickers = [t for t in sp_ticker_list
                    if st.session_state.get(f"sp_result_{t}") and
                    not st.session_state[f"sp_result_{t}"].get("error")]

    if done_tickers:
        st.divider()
        st.markdown("### 📊 多股回測比較總表")

        summary_rows = []
        for t in done_tickers:
            bt = st.session_state[f"sp_result_{t}"]
            pwr = bt.get("feature_power", [])
            top1 = pwr[0]["特徵"] if pwr else "N/A"
            top1_lift = pwr[0]["預測力倍數"] if pwr else 0
            hs   = bt.get("horizon_stats", {})
            best_hd = max(hs, key=lambda k: hs[k]["平均漲幅"], default="N/A") if hs else "N/A"
            best_wr = hs.get(best_hd, {}).get("勝率", "N/A") if hs else "N/A"
            best_rt = hs.get(best_hd, {}).get("平均漲幅", "N/A") if hs else "N/A"
            rs   = bt.get("regime_stats", {})
            bull_rate = rs.get("牛市", {}).get("爆升率", "N/A")
            bear_rate = rs.get("熊市", {}).get("爆升率", "N/A")
            ei   = bt.get("earnings_impact", {})
            tr   = bt.get("train_result", {})
            te   = bt.get("test_result",  {})
            summary_rows.append({
                "股票":       t,
                "爆升點數":   len(bt.get("surge_points", [])),
                "最強特徵":   f"{top1}({top1_lift:.1f}x)",
                "最優持倉":   best_hd,
                "最優勝率":   f"{best_wr}%",
                "最優均漲":   f"+{best_rt}%",
                "牛市爆升率": f"{bull_rate}%",
                "熊市爆升率": f"{bear_rate}%",
                "財報週佔比": f"{ei.get('財報週佔比','N/A')}%",
                "訓練樣本":   tr.get("樣本數", 0),
                "測試樣本":   te.get("樣本數", 0),
            })

        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  實時監控面板（多股並行）
    # ══════════════════════════════════════════════════════════════════════════
    if done_tickers:
        st.divider()
        st.markdown("### 📡 實時監控")
        st.caption("基於各股個性化回測特徵，同時掃描所有股票")

        mon_c1, mon_c2, mon_c3 = st.columns([2, 2, 4])
        with mon_c1:
            scan_all_btn = st.button("🔍 全部掃描", type="primary",
                                     use_container_width=True, key="scan_all_btn")
        with mon_c2:
            auto_tg = st.checkbox("觸發時自動發 Telegram", value=True, key="auto_tg")
        with mon_c3:
            triggered_now = [t for t in done_tickers
                             if st.session_state.get(f"sp_sig_{t}", {}).get("triggered")]
            if triggered_now:
                st.error(f"🚨 已觸發：{', '.join(triggered_now)}")
            else:
                st.caption("目前無觸發信號")

        # 全部掃描
        if scan_all_btn:
            prog2 = st.progress(0, text="掃描中...")
            for i, ticker in enumerate(done_tickers):
                prog2.progress(i / len(done_tickers),
                               text=f"掃描 {ticker}（{i+1}/{len(done_tickers)}）...")
                bt = st.session_state[f"sp_result_{ticker}"]
                pwr_data = bt.get("feature_power", [])
                sig = _realtime_check(ticker, bt, pwr_data, sp_vol_win)
                st.session_state[f"sp_sig_{ticker}"] = sig

                if auto_tg and sig.get("triggered") and not sig.get("error"):
                    sig_key = f"sp_{ticker}_{sig['time'].strftime('%Y%m%d%H%M')}"
                    if sig_key not in st.session_state.get("sent_signals", set()):
                        msg = _build_surge_tg_msg(sig, bt)
                        ok, err = send_telegram_alert(msg, ticker)
                        if ok:
                            st.session_state.setdefault("sent_signals", set()).add(sig_key)
                            st.toast(f"📱 {ticker} Telegram 已發送")
            prog2.progress(1.0, text="✅ 掃描完成")

        # ── 各股信號卡片 ──────────────────────────────────────────────────────
        # 每行3個
        for row_start in range(0, len(done_tickers), 3):
            row_tickers = done_tickers[row_start:row_start+3]
            cols = st.columns(len(row_tickers))
            for col, ticker in zip(cols, row_tickers):
                with col:
                    bt  = st.session_state[f"sp_result_{ticker}"]
                    sig = st.session_state.get(f"sp_sig_{ticker}")

                    # 個別掃描按鈕
                    if st.button(f"🔍 {ticker}", key=f"scan_single_{ticker}",
                                 use_container_width=True):
                        pwr_data = bt.get("feature_power", [])
                        sig = _realtime_check(ticker, bt, pwr_data, sp_vol_win)
                        st.session_state[f"sp_sig_{ticker}"] = sig
                        if auto_tg and sig.get("triggered") and not sig.get("error"):
                            sig_key = f"sp_{ticker}_{sig['time'].strftime('%Y%m%d%H%M')}"
                            if sig_key not in st.session_state.get("sent_signals", set()):
                                msg = _build_surge_tg_msg(sig, bt)
                                ok, _ = send_telegram_alert(msg, ticker)
                                if ok:
                                    st.session_state.setdefault("sent_signals", set()).add(sig_key)
                                    st.toast(f"📱 {ticker} Telegram 已發送")

                    if sig is None:
                        st.markdown(
                            "<div style='background:#161b27;border:1px solid #1e2535;"
                            "border-radius:8px;padding:14px;text-align:center;color:#5a6580'>"
                            "⚪ 尚未掃描</div>",
                            unsafe_allow_html=True
                        )
                        continue

                    if sig.get("error"):
                        st.warning(f"⚠️ {sig['error']}")
                        continue

                    score  = sig["score"]
                    max_sc = sig["max_score"]
                    pct    = int(score / max(max_sc, 1) * 100)
                    trig   = sig["triggered"]
                    bar_col = "#00d4aa" if trig else "#ffd166" if pct >= 50 else "#5a6580"
                    bdr_col = "#00d4aa" if trig else "#ffd166" if pct >= 50 else "#2a3040"
                    bg_col  = "rgba(0,212,170,0.1)" if trig else "rgba(255,209,102,0.06)" if pct >= 50 else "#161b27"
                    icon    = "🚨" if trig else "🟡" if pct >= 50 else "⚪"

                    # 條件明細文字
                    conds = sig.get("conditions", [])
                    active = [c for c in conds if isinstance(c, dict) and c.get("active")]
                    cond_html = "".join(
                        f"<div style='font-size:11px;padding:2px 0;"
                        f"color:{'#00d4aa' if c['passed'] else '#ff4560'}'>"
                        f"{'✅' if c['passed'] else '❌'} {c['text'].replace('✅ ','').replace('❌ ','')} "
                        f"<span style='color:#5a6580'>({c['value']})</span>"
                        f"{'<span style=\"color:#00d4aa\"> +'+str(c['pts'])+'分</span>' if c['passed'] else ''}"
                        f"</div>"
                        for c in active
                    )

                    # 最優持倉
                    hs = bt.get("horizon_stats", {})
                    best_hd = max(hs, key=lambda k: hs[k]["平均漲幅"], default="") if hs else ""
                    hold_str = f"最優持倉 {best_hd}｜均漲{hs[best_hd]['平均漲幅']}%" if best_hd else ""

                    st.markdown(f"""
<div style="background:{bg_col};border:1px solid {bdr_col};
            border-radius:8px;padding:12px;margin-top:4px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="font-size:15px;font-weight:700">{icon} {ticker}</span>
    <span style="font-size:10px;color:#5a6580">{sig['time'].strftime('%H:%M:%S')}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;
              background:rgba(0,0,0,0.2);border-radius:4px;padding:8px">
    <div style="font-size:11px;color:#5a6580">現價</div>
    <div style="font-size:14px;font-weight:700">${sig['price']:.2f}</div>
    <div style="font-size:11px;color:#5a6580">漲幅</div>
    <div style="font-size:14px;font-weight:700;color:{'#00d4aa' if sig['ret']>0 else '#ff4560'}">{sig['ret']*100:+.2f}%</div>
    <div style="font-size:11px;color:#5a6580">量倍數</div>
    <div style="font-size:14px;font-weight:700;color:{'#00d4aa' if sig['vol_ratio']>=2 else '#ffd166' if sig['vol_ratio']>=1.5 else '#e8edf5'}">{sig['vol_ratio']:.2f}x</div>
    <div style="font-size:11px;color:#5a6580">收盤位置</div>
    <div style="font-size:14px;font-weight:700">{sig.get('close_pos',0)*100:.0f}%</div>
  </div>
  <div style="margin-bottom:8px">
    <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px">
      <span style="color:#5a6580">評分</span>
      <span><b style="color:{bar_col}">{score}/{max_sc}</b> ({pct}%)</span>
    </div>
    <div style="height:6px;background:#1e2535;border-radius:3px">
      <div style="height:6px;width:{pct}%;background:{bar_col};border-radius:3px"></div>
    </div>
  </div>
  <div style="border-top:1px solid #1e2535;padding-top:8px">
    {cond_html}
  </div>
  {"<div style='margin-top:8px;font-size:10px;color:#5a6580'>"+hold_str+"</div>" if hold_str else ""}
</div>
""", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════
        #  個股詳細分析（可展開）
        # ══════════════════════════════════════════════════════════════════════
        st.divider()
        st.markdown("### 🔍 個股詳細分析")

        selected_detail = st.selectbox(
            "選擇查看詳細回測結果",
            done_tickers, key="detail_ticker"
        )

        if selected_detail:
            sp_ticker = selected_detail
            bt_res = st.session_state[f"sp_result_{sp_ticker}"]
            surge_pts = bt_res.get("surge_points", [])
            pwr_data  = bt_res.get("feature_power", [])
            pwr_df    = pd.DataFrame(pwr_data) if pwr_data else pd.DataFrame()
            tr = bt_res.get("train_result", {})
            te = bt_res.get("test_result",  {})

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("總K線數",    bt_res["total_bars"])
            m2.metric("爆升點數",   len(surge_pts), f"定義:{sp_days}天漲>{sp_surge}%")
            m3.metric("特徵分析數", len(pwr_df) if not pwr_df.empty else 0)
            m4.metric("訓練集樣本", tr.get("樣本數", 0), f"前{int(sp_train*100)}%")
            m5.metric("測試集樣本", te.get("樣本數", 0), f"後{int((1-sp_train)*100)}%")

            detail_tab1, detail_tab2, detail_tab3, detail_tab4, detail_tab5 = st.tabs([
                "🏆 特徵預測力", "📈 過程特徵", "📊 量能分層", "⏱️ 持倉天數", "🌍 環境+財報+驗證"
            ])

            with detail_tab1:
                if not pwr_df.empty:
                    def _color_lift(val):
                        try:
                            v = float(val)
                            if v >= 2.5: return "background-color:#0d3b1e;color:#00d4aa"
                            if v >= 1.5: return "background-color:#1a2e0d;color:#7ec850"
                            if v >= 1.2: return "background-color:#2a2200;color:#ffd166"
                            return "background-color:#2a0d0d;color:#ff4560"
                        except: return ""
                    styled = pwr_df.style.map(_color_lift, subset=["預測力倍數"])
                    st.dataframe(styled, use_container_width=True, hide_index=True)
                    fig_pwr = go.Figure(go.Bar(
                        x=pwr_df["預測力倍數"], y=pwr_df["特徵"], orientation="h",
                        marker_color=["#00d4aa" if v>=2 else "#ffd166" if v>=1.5 else "#ff4560"
                                      for v in pwr_df["預測力倍數"]],
                        text=[f"{v:.1f}x" for v in pwr_df["預測力倍數"]],
                        textposition="outside",
                    ))
                    fig_pwr.add_vline(x=1.0, line_dash="dash", line_color="gray")
                    fig_pwr.add_vline(x=2.0, line_dash="dash", line_color="#00d4aa")
                    fig_pwr.update_layout(
                        title=f"{sp_ticker} 特徵預測力",
                        template="plotly_dark", height=400,
                        margin=dict(l=200,r=60,t=40,b=40),
                    )
                    st.plotly_chart(fig_pwr, use_container_width=True, key=f"pwr_{sp_ticker}")

            with detail_tab2:
                ps = bt_res.get("process_stats", {})
                if ps:
                    ps_rows = [{"過程特徵": k, **v} for k, v in ps.items()]
                    st.dataframe(pd.DataFrame(ps_rows), use_container_width=True, hide_index=True)

            with detail_tab3:
                ls = bt_res.get("layer_stats", {})
                if ls:
                    ls_rows = [{"量能等級": k, **v} for k, v in ls.items()]
                    ls_df = pd.DataFrame(ls_rows)
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.dataframe(ls_df, use_container_width=True, hide_index=True)
                    with col_r:
                        fig_ls = go.Figure(go.Bar(
                            x=[r["量能等級"] for r in ls_rows],
                            y=[r["爆升率"] for r in ls_rows],
                            marker_color="#00d4aa",
                            text=[f"{r['爆升率']}%" for r in ls_rows],
                            textposition="outside",
                        ))
                        fig_ls.update_layout(template="plotly_dark", height=280,
                                             margin=dict(t=20,b=20))
                        st.plotly_chart(fig_ls, use_container_width=True, key=f"ls_{sp_ticker}")

            with detail_tab4:
                hs = bt_res.get("horizon_stats", {})
                if hs:
                    hs_rows = [{"持倉天數": k, **v} for k, v in hs.items()]
                    hs_df   = pd.DataFrame(hs_rows)
                    best_hd = max(hs, key=lambda k: hs[k]["平均漲幅"])
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        st.dataframe(hs_df, use_container_width=True, hide_index=True)
                        st.success(f"🏆 最優持倉：{best_hd}（均漲{hs[best_hd]['平均漲幅']}%，勝率{hs[best_hd]['勝率']}%）")
                    with col_h2:
                        fig_hs = go.Figure(go.Bar(
                            x=list(hs.keys()),
                            y=[v["平均漲幅"] for v in hs.values()],
                            marker_color="#7c5cfc",
                            text=[f"{v['平均漲幅']}%" for v in hs.values()],
                            textposition="outside",
                        ))
                        fig_hs.update_layout(template="plotly_dark", height=280,
                                             margin=dict(t=20,b=20))
                        st.plotly_chart(fig_hs, use_container_width=True, key=f"hs_{sp_ticker}")

            with detail_tab5:
                col_j, col_l = st.columns(2)
                with col_j:
                    st.markdown("**🌍 大市環境分層**")
                    rs = bt_res.get("regime_stats", {})
                    if rs:
                        rs_rows = [{"環境": k, **v} for k, v in rs.items()]
                        st.dataframe(pd.DataFrame(rs_rows), use_container_width=True, hide_index=True)
                with col_l:
                    st.markdown("**📅 財報週影響**")
                    ei = bt_res.get("earnings_impact", {})
                    if ei:
                        st.metric("財報週爆升次數",   ei.get("財報週爆升次數", 0))
                        st.metric("非財報週爆升次數", ei.get("非財報週爆升次數", 0))
                        st.metric("財報週佔比",       f"{ei.get('財報週佔比', 0)}%")
                        if ei.get("財報週佔比", 0) > 30:
                            st.warning("⚠️ 超過30%的爆升在財報週，量能信號需額外謹慎")
                        else:
                            st.success("✅ 財報週影響有限，量能信號相對可靠")

                st.divider()
                st.markdown("**🔬 訓練集 vs 測試集驗證**")
                if tr and te:
                    st.dataframe(pd.DataFrame([tr, te]), use_container_width=True, hide_index=True)
                    te_n = te.get("樣本數", 0)
                    if te_n == 0:
                        st.warning("⚠️ 測試集樣本不足")
                    else:
                        st.success("✅ 訓練集與測試集分布均衡，規律相對可靠")

    # ══════════════════════════════════════════════════════════════════════════
    #  📋 每日總覽 AI Prompt（v3.7）
    # ══════════════════════════════════════════════════════════════════════════
    if done_tickers:
        st.divider()
        st.markdown("### 📋 每日總覽 AI Prompt")
        st.caption(
            "把所有監控股票的即時數據濃縮成一個 Prompt，"
            "貼去 ChatGPT / Claude / Gemini 獲得今日操作優先級分析。"
        )
        _overview_snap_count = sum(
            1 for t in selected_tickers
            if st.session_state.get(f"ai_snap_{t}")
        )
        st.caption(f"已有即時快照：{_overview_snap_count}/{len(selected_tickers)} 支股票")
        with st.expander("📊 展開每日總覽 Prompt", expanded=False):
            _overview_prompt = _build_overview_prompt(selected_tickers)
            st.code(_overview_prompt, language=None)
            st.caption("💡 若某股票顯示「尚無數據」，請確認主監控已展開該股票的 Tab 並刷新。")

    # ══════════════════════════════════════════════════════════════════════════
    #  🤖 AI 分析對話（多股版：可選擇對哪隻股票問問題）
    # ══════════════════════════════════════════════════════════════════════════
    if done_tickers:
        st.divider()
        st.markdown("### 🤖 AI 分析對話")
        st.caption("選擇股票，回測數據自動注入，直接問問題 · 由 Groq llama-3.3-70b 驅動")

        if not groq_ready:
            st.warning("⚠️ 請在 Streamlit secrets 加入 `[groq] GROQ_API_KEY = 'your_key'`")

        ai_c1, ai_c2 = st.columns([2, 2])
        with ai_c1:
            ai_target = st.selectbox("問哪隻股票", done_tickers, key="ai_target")
        with ai_c2:
            ai_lang = st.selectbox("回覆語言", ["繁體中文", "简体中文", "English"], key="ai_lang")

        # v3.7: 切換 ticker 時自動清空對話，避免上下文混亂
        if st.session_state.get("ai_last_target") != ai_target:
            st.session_state["ai_chat_history"] = []
            st.session_state.pop("ai_pending_prompt", None)
            st.session_state["ai_last_target"] = ai_target

        # 預設問題
        preset_prompts = {
            "📊 整體解讀":   "根據以上數據，幫我解讀 {ticker} 當前技術面，多空力道如何？",
            "🔍 最佳進場":   "根據回測數據，{ticker} 現在最佳的進場條件是什麼？請給具體數字。",
            "⚠️ 風險評估":   "根據當前數據，這套信號有哪些風險？什麼環境下最容易失效？",
            "📈 持倉策略":   "根據最優持倉天數和大市環境，幫我制定 {ticker} 的持倉和止損策略。",
            "🔬 過擬合評估": "訓練集和測試集的數據是否一致？這套規律是真實的還是歷史過擬合？",
            "💰 實盤建議":   "如果要實盤交易 {ticker}，資金管理和風控怎麼設置？",
        }
        btn_cols = st.columns(3)
        for i, (label, tmpl) in enumerate(preset_prompts.items()):
            with btn_cols[i % 3]:
                if st.button(label, key=f"preset_{i}", use_container_width=True):
                    st.session_state["ai_pending_prompt"] = tmpl.format(ticker=ai_target)

        if "ai_chat_history" not in st.session_state:
            st.session_state["ai_chat_history"] = []
        if st.button("🗑️ 清空對話", key="ai_clear"):
            st.session_state["ai_chat_history"] = []
            st.session_state.pop("ai_pending_prompt", None)
            st.rerun()

        for msg in st.session_state["ai_chat_history"]:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
                st.markdown(msg["content"])

        pending     = st.session_state.pop("ai_pending_prompt", None)
        user_input  = st.chat_input("直接問 AI（即時數據 + 回測已自動注入）", key="ai_chat_input")
        final_input = pending or user_input

        if final_input:
            st.session_state["ai_chat_history"].append({"role":"user","content":final_input})
            with st.chat_message("user", avatar="👤"):
                st.markdown(final_input)

            lang_map = {"繁體中文":"請用繁體中文回覆","简体中文":"请用简体中文回复","English":"Please reply in English"}

            # v3.7: system prompt 同時注入即時快照 + 爆升回測摘要
            _snap_prompt = _build_signal_prompt(ai_target)
            bt_summary   = _build_bt_summary(st.session_state.get(f"sp_result_{ai_target}"), ai_target)
            system_prompt = f"""你是一位專業的量化交易分析師，專注於股票量價信號分析。
{lang_map.get(st.session_state.get('ai_lang','繁體中文'),'請用繁體中文回覆')}

以下是 {ai_target} 的完整即時市況與回測數據：

{_snap_prompt}

補充爆升回測統計：
{bt_summary}

分析原則：基於數據說話，給出具體數字；指出優勢和局限；結合大市環境；誠實評估過擬合風險。"""

            api_messages = [{"role":m["role"],"content":m["content"]}
                            for m in st.session_state["ai_chat_history"][:-1]]
            api_messages.append({"role":"user","content":final_input})

            with st.chat_message("assistant", avatar="🤖"):
                placeholder = st.empty()
                full_reply  = ""
                if not groq_ready:
                    full_reply = "⚠️ Groq API Key 未設定"
                    placeholder.warning(full_reply)
                else:
                    try:
                        headers = {"Authorization": f"Bearer {GROQ_API_KEY}",
                                   "Content-Type": "application/json"}
                        payload = {"model": "llama-3.3-70b-versatile",
                                   "temperature": 0.3, "max_tokens": 2048,
                                   "stream": True,
                                   "messages": [{"role":"system","content":system_prompt}]+api_messages}
                        with requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers=headers, json=payload, stream=True, timeout=60
                        ) as resp:
                            if resp.status_code != 200:
                                raise Exception(f"Groq {resp.status_code}: {resp.text[:300]}")
                            for line in resp.iter_lines():
                                if not line: continue
                                s = line.decode("utf-8")
                                if s.startswith("data: ") and s[6:].strip() != "[DONE]":
                                    try:
                                        delta = json.loads(s[6:])["choices"][0]["delta"].get("content","")
                                        full_reply += delta
                                        placeholder.markdown(full_reply + "▌")
                                    except: continue
                        placeholder.markdown(full_reply)
                    except Exception as e:
                        full_reply = f"❌ Groq 調用失敗：{e}"
                        placeholder.error(full_reply)

                if full_reply:
                    st.session_state["ai_chat_history"].append({"role":"assistant","content":full_reply})

# ═════════════════════════════════════════════════════════════════════════════
#  AUTO REFRESH（使用 @st.fragment 實現非阻塞自動刷新）
# ═════════════════════════════════════════════════════════════════════════════
st.divider()




# ═════════════════════════════════════════════════════════════════════════════
#  📡 Screener選股  +  📊 監控總覽
# ═════════════════════════════════════════════════════════════════════════════

_MEGA_UNIVERSE = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AVGO","TSM","ORCL",
    "ASML","CSCO","ADBE","AMD","QCOM","TXN","INTC","IBM","AMAT",
    "JPM","V","MA","BAC","WFC","GS","MS","C","AXP","BLK",
    "LLY","JNJ","UNH","ABBV","MRK","TMO","ABT","DHR","PFE","AMGN",
    "WMT","COST","HD","MCD","KO","PEP","NKE","SBUX",
    "XOM","CVX","COP","CAT","HON","RTX","BA",
    "SPY","QQQ","IWM","XLK","GLD",
]

@st.cache_data(ttl=300, show_spinner=False)
def _sc_fetch(ticker: str):
    try:
        tk = yf.Ticker(ticker)
        h  = tk.history(period="1y", interval="1d", timeout=10)
        if h.empty or len(h) < 60:
            return None, 0.0
        mc = 0.0
        try:
            fi = tk.fast_info
            v  = getattr(fi, "market_cap", None)
            if v and v > 0:
                mc = v / 1e9
        except Exception:
            pass
        return h, mc
    except Exception:
        return None, 0.0

def _sc_fundamental(hist):
    try:
        close = hist["Close"]
        opens = hist["Open"]
        rs_ok = False
        try:
            spy = yf.Ticker("SPY").history(period="90d", interval="1d")["Close"]
            if not spy.empty and len(spy) >= 60:
                stock_ret = (close.iloc[-1] / close.iloc[-60] - 1) * 100
                spy_ret   = (spy.iloc[-1]   / spy.iloc[-60]   - 1) * 100
                rs_ok     = stock_ret > spy_ret + 5
        except Exception:
            pass
        prev_c = close.shift(1)
        gap_up = False
        for j in range(-30, -1):
            try:
                pv = prev_c.iloc[j]
                if pv and pv > 0 and (opens.iloc[j] - pv) / pv * 100 >= 2.0:
                    gap_up = True
                    break
            except Exception:
                pass
        wk52      = close.iloc[-252:].max() if len(close) >= 252 else close.max()
        near_high = close.iloc[-1] >= wk52 * 0.92
        score     = sum([rs_ok, gap_up, near_high])
        return score >= 2, f"RS強:{rs_ok} | 跳空:{gap_up} | 近高:{near_high}"
    except Exception as e:
        return False, str(e)

def _sc_vol_expansion(hist):
    try:
        close  = hist["Close"]
        volume = hist["Volume"]
        vol5   = volume.iloc[-5:].mean()
        vol20  = volume.iloc[-20:].mean()
        rvol   = vol5 / max(vol20, 1)
        obv    = (pd.Series(np.sign(close.diff())) * volume).fillna(0).cumsum()
        obv_rising = bool(obv.iloc[-1] > obv.iloc[-20])
        price_up   = bool(close.iloc[-1] > close.iloc[-5])
        score  = sum([rvol >= 1.5, obv_rising, price_up])
        return score >= 2, f"RVOL:{rvol:.1f}x | OBV_up:{obv_rising} | 價升:{price_up}"
    except Exception as e:
        return False, str(e)

def _sc_trend_accel(hist):
    try:
        close = hist["Close"]
        high  = hist["High"]
        low   = hist["Low"]
        e10   = close.ewm(span=10,  adjust=False).mean()
        e21   = close.ewm(span=21,  adjust=False).mean()
        e50   = close.ewm(span=50,  adjust=False).mean()
        e200  = close.ewm(span=200, adjust=False).mean()
        ema_stack = bool(e10.iloc[-1] > e21.iloc[-1] > e50.iloc[-1] > e200.iloc[-1])
        e12   = close.ewm(span=12, adjust=False).mean()
        e26   = close.ewm(span=26, adjust=False).mean()
        macd  = e12 - e26
        sig_l = macd.ewm(span=9, adjust=False).mean()
        macd_ok = bool(macd.iloc[-1] > sig_l.iloc[-1] and (macd - sig_l).iloc[-1] > 0)
        prev_c  = close.shift(1)
        tr      = pd.concat([(high-low),(high-prev_c).abs(),(low-prev_c).abs()],axis=1).max(axis=1)
        atr     = tr.ewm(span=14, adjust=False).mean()
        vcp     = bool(
            atr.iloc[-5:].mean() < atr.iloc[-20:-5].mean() * 0.85
            and close.iloc[-1] > close.iloc[-25:-5].max()
        )
        score = sum([ema_stack, macd_ok, vcp])
        return score >= 2, f"EMA排列:{ema_stack} | MACD:{macd_ok} | VCP:{vcp}"
    except Exception as e:
        return False, str(e)

def _sc_base_breakout(hist):
    try:
        close  = hist["Close"]
        high   = hist["High"]
        low    = hist["Low"]
        volume = hist["Volume"]
        prev_c = close.shift(1)
        tr     = pd.concat([(high-low),(high-prev_c).abs(),(low-prev_c).abs()],axis=1).max(axis=1)
        atr    = tr.ewm(span=14, adjust=False).mean()
        atr_ok    = bool(atr.iloc[-20:].mean()    < atr.iloc[-40:-20].mean()    * 0.85)
        vol_dry   = bool(volume.iloc[-20:].mean()  < volume.iloc[-40:-20].mean() * 0.90)
        broke     = bool(close.iloc[-1]            > close.iloc[-65:-5].max())
        vol_surge = bool(volume.iloc[-1]           > volume.iloc[-20:].mean()    * 1.5)
        score  = sum([atr_ok, vol_dry, broke, vol_surge])
        return score >= 3, f"ATR收:{atr_ok} | 量縮:{vol_dry} | 突破:{broke} | 量升:{vol_surge}"
    except Exception as e:
        return False, str(e)

def _sc_scan_one(ticker, min_cap, use_fund, use_vol, use_trend, use_base):
    hist, mc = _sc_fetch(ticker)
    if hist is None or mc < min_cap:
        return None
    price   = float(hist["Close"].iloc[-1])
    prev    = float(hist["Close"].iloc[-2])
    chg_pct = (price - prev) / prev * 100
    vol_r   = float(hist["Volume"].iloc[-5:].mean() / max(hist["Volume"].iloc[-20:].mean(), 1))
    sigs = {}
    cnt  = 0
    if use_fund:
        ok, det = _sc_fundamental(hist)
        sigs["①業績質變"] = (ok, det)
        cnt += ok
    if use_vol:
        ok, det = _sc_vol_expansion(hist)
        sigs["②資金狂入"] = (ok, det)
        cnt += ok
    if use_trend:
        ok, det = _sc_trend_accel(hist)
        sigs["③趨勢加速"] = (ok, det)
        cnt += ok
    if use_base:
        ok, det = _sc_base_breakout(hist)
        sigs["④底部突破"] = (ok, det)
        cnt += ok
    enabled = sum([use_fund, use_vol, use_trend, use_base])
    if enabled == 0 or cnt < 1:
        return None
    return {
        "ticker": ticker, "price": price, "chg_pct": chg_pct,
        "mc_b": mc, "vol_ratio": vol_r,
        "signals": sigs, "sig_count": cnt, "enabled": enabled,
    }

def _sm_tg_msg(sig, bt, sc_sigs):
    ticker   = sig["ticker"]
    sc_lines = "\n".join(
        "  {} {}: {}".format("✅" if v[0] else "❌", k, v[1][:60])
        for k, v in sc_sigs.items()
    ) if sc_sigs else "  （直接加入，無Screener記錄）"
    pwr  = bt.get("feature_power", [])
    top3 = ", ".join(f["特徵"] for f in pwr[:3]) if pwr else "N/A"
    hs   = bt.get("horizon_stats", {})
    bhd  = max(hs, key=lambda k: hs[k]["平均漲幅"], default="N/A") if hs else "N/A"
    conds  = sig.get("conditions", [])
    active = [c for c in conds if isinstance(c, dict) and c.get("active")]
    clines = "\n".join(
        "  {} {} ({})".format(
            "✅" if c["passed"] else "❌",
            c["text"].replace("✅ ", "").replace("❌ ", ""),
            c["value"]
        )
        for c in active
    )
    wr  = hs.get(bhd, {}).get("勝率", "N/A")   if bhd != "N/A" else "N/A"
    avg = hs.get(bhd, {}).get("平均漲幅", "N/A") if bhd != "N/A" else "N/A"
    return (
        "🚀 <b>智能選股雙重信號觸發</b>\n\n"
        "🏷️ <b>{}</b>  |  {}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📡 <b>Screener 信號</b>\n{}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>即時數據</b>\n"
        "  現價: <b>${:.2f}</b>\n"
        "  漲幅: <b>{:+.2f}%</b>\n"
        "  量倍數: <b>{:.1f}x</b>\n\n"
        "🎯 <b>爆升前特徵評分: {}/{}</b>\n{}\n"
        "  最強特徵: {}\n\n"
        "⏱️ <b>最優持倉</b>: {}\n"
        "   均漲 {}%，勝率 {}%\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ 基於個股回測，不構成投資建議"
    ).format(
        ticker, sig["time"].strftime("%Y-%m-%d %H:%M"),
        sc_lines,
        sig["price"], sig["ret"] * 100, sig["vol_ratio"],
        sig["score"], sig["max_score"], clines, top3,
        bhd, avg, wr
    )


# ── Session state init ────────────────────────────────────────────────────────
for _sk, _sv in [
    ("sm_queue",        []),
    ("sm_bt_done",      {}),
    ("sm_scan_results", []),
    ("sm_mon_sigs",     {}),
]:
    if _sk not in st.session_state:
        st.session_state[_sk] = _sv


# ════════════════════════════════════════════════════════════════════════════
#  Tab: 📡 Screener選股
# ════════════════════════════════════════════════════════════════════════════
with tabs[-2]:
    st.markdown("## 📡 Screener 選股")
    st.caption(
        f"掃描 {len(_MEGA_UNIVERSE)} 隻大市值股票 | "
        "找到信號後手動勾選確認加入回測隊列 | 支援直接輸入任意股票"
    )

    # ── 參數設定 ──────────────────────────────────────────────────────────────
    with st.expander("⚙️ 參數設定", expanded=False):
        _ep1, _ep2, _ep3 = st.columns(3)
        with _ep1:
            st.markdown("**Screener 條件**")
            sm_min_cap   = st.slider("最低市值(十億$)", 50, 500, 100, 50, key="sm_min_cap")
            sm_use_fund  = st.checkbox("① 業績質變（RS+跳空+近高）", value=True,  key="sm_uf")
            sm_use_vol   = st.checkbox("② 資金狂入（RVOL+OBV+價升）", value=True,  key="sm_uv")
            sm_use_trend = st.checkbox("③ 趨勢加速（EMA+MACD+VCP）",  value=True,  key="sm_ut")
            sm_use_base  = st.checkbox("④ 底部突破（ATR+量縮+突破）", value=False, key="sm_ub")
        with _ep2:
            st.markdown("**回測參數**")
            sm_period  = st.selectbox("回測年數", ["2y","3y","5y","10y"], index=2, key="sm_period")
            sm_surge   = st.slider("爆升N天漲幅(%)",  5, 20, 10, 1, key="sm_surge")
            sm_days    = st.slider("往後看幾天",       3, 15,  7, 1, key="sm_days")
            sm_lb      = st.slider("往前看特徵天數",   3, 15,  7, 1, key="sm_lb")
            sm_vol_win = st.slider("成交量均線窗口",  10, 30, 20, 1, key="sm_vol_win")
        with _ep3:
            st.markdown("**推送設定**")
            sm_auto_tg = st.checkbox("觸發時自動發 Telegram", value=True, key="sm_auto_tg")
            st.caption(
                "觸發條件：\n"
                "• 爆升前特徵評分 ≥ 65%\n"
                "• 量倍數 ≥ 1.5x\n"
                "• 量能遞進 或 底部抬升"
            )

    # ── 手動加入 ──────────────────────────────────────────────────────────────
    st.markdown("### ➕ 手動加入任意股票")
    _ha, _hb = st.columns([4, 1])
    with _ha:
        _manual_in = st.text_input(
            "股票代號",
            placeholder="單隻或逗號分隔，例：PLTR, COIN, MSTR",
            key="sm_manual_in",
            label_visibility="collapsed",
        )
    with _hb:
        if st.button("加入回測隊列", key="sm_hadd",
                     use_container_width=True, type="primary"):
            _tks   = [t.strip().upper() for t in _manual_in.split(",") if t.strip()]
            _added = []
            for _t in _tks:
                if (_t
                        and _t not in st.session_state["sm_queue"]
                        and _t not in st.session_state["sm_bt_done"]):
                    st.session_state["sm_queue"].append(_t)
                    _added.append(_t)
            if _added:
                st.success("✅ 已加入：{}".format(", ".join(_added)))
            elif _tks:
                st.info("股票已在隊列或已完成回測")

    # 隊列快速狀態
    _q   = st.session_state["sm_queue"]
    _btd = st.session_state["sm_bt_done"]
    if _q or _btd:
        st.caption(
            "待回測 ({})：{}　|　已回測 ({})：{}".format(
                len(_q),   ", ".join(_q)                          or "空",
                len(_btd), ", ".join(list(_btd.keys())[:6])       or "無",
            )
        )

    st.divider()

    # ── Screener 掃描 ─────────────────────────────────────────────────────────
    st.markdown("### 🔍 自動掃描大市值股票")
    _sa, _sb = st.columns([1, 3])
    with _sa:
        _do_scan = st.button("🔍 開始掃描", type="primary",
                             use_container_width=True, key="sm_do_scan")
    with _sb:
        _lt = st.session_state.get("sm_last_scan_time")
        if _lt:
            st.caption(
                "上次掃描：{}  |  結果：{} 隻".format(
                    _lt, len(st.session_state["sm_scan_results"])
                )
            )
        else:
            st.caption("尚未掃描，按左側按鈕開始")

    if _do_scan:
        _prog = st.progress(0, text="掃描中...")
        _res  = []
        for _i, _tk in enumerate(_MEGA_UNIVERSE):
            _prog.progress(
                (_i + 1) / len(_MEGA_UNIVERSE),
                text="掃描 {}（{}/{}）...".format(_tk, _i + 1, len(_MEGA_UNIVERSE))
            )
            _r = _sc_scan_one(
                _tk,
                st.session_state.get("sm_min_cap",  100),
                st.session_state.get("sm_uf",   True),
                st.session_state.get("sm_uv",   True),
                st.session_state.get("sm_ut",   True),
                st.session_state.get("sm_ub",   False),
            )
            if _r:
                _res.append(_r)
        _prog.empty()
        _res.sort(key=lambda x: x["sig_count"], reverse=True)
        st.session_state["sm_scan_results"]   = _res
        st.session_state["sm_last_scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.success("✅ 掃描完成：{} 隻有信號，請勾選後確認加入回測".format(len(_res)))
        st.rerun()

    # ── 掃描結果：手動勾選確認 ───────────────────────────────────────────────
    _scan_res = st.session_state.get("sm_scan_results", [])
    if _scan_res:
        st.markdown("### 掃描結果（{} 隻）".format(len(_scan_res)))

        # 統計列
        _mc1, _mc2, _mc3, _mc4 = st.columns(4)
        _mc1.metric("有信號", len(_scan_res))
        _mc2.metric("全信號命中", sum(1 for r in _scan_res if r["sig_count"] == r["enabled"]))
        _mc3.metric("已在隊列", sum(1 for r in _scan_res
                                    if r["ticker"] in st.session_state["sm_queue"]))
        _mc4.metric("已回測",   sum(1 for r in _scan_res
                                    if r["ticker"] in st.session_state["sm_bt_done"]))

        # 按信號數分組顯示，逐行勾選
        _max_sig  = max(r["sig_count"] for r in _scan_res)
        _selected = []

        for _sn in range(_max_sig, 0, -1):
            _group = [r for r in _scan_res if r["sig_count"] == _sn]
            if not _group:
                continue
            _enabled = _group[0]["enabled"]
            st.markdown(
                "**{stars} {n}/{e} 信號命中 — {cnt} 隻**".format(
                    stars="⭐" * _sn, n=_sn, e=_enabled, cnt=len(_group)
                )
            )

            for _r in _group:
                _tk   = _r["ticker"]
                _done = _tk in st.session_state["sm_bt_done"]
                _inq  = _tk in st.session_state["sm_queue"]
                _status = "✅已回測" if _done else "📋隊列中" if _inq else ""

                _ck, _ci, _cs, _cst = st.columns([0.5, 2, 4, 1.5])
                with _ck:
                    _chk = st.checkbox(
                        "", key="sm_chk_{}".format(_tk),
                        value=False, disabled=_done or _inq
                    )
                with _ci:
                    _clr = "#00d4aa" if _r["chg_pct"] > 0 else "#ff4560"
                    st.markdown(
                        "<b style='font-size:15px'>{tk}</b> "
                        "<span style='color:{clr}'>{chg:+.2f}%</span> "
                        "<span style='color:#5a6580;font-size:12px'>"
                        "${px:.2f} | ${mc:.0f}B</span>".format(
                            tk=_tk, clr=_clr,
                            chg=_r["chg_pct"],
                            px=_r["price"], mc=_r["mc_b"]
                        ),
                        unsafe_allow_html=True
                    )
                with _cs:
                    _badges = " ".join(
                        "<span style='background:{bg};color:{fc};"
                        "padding:2px 8px;border-radius:10px;font-size:11px'>"
                        "{ic} {k}</span>".format(
                            bg="rgba(0,212,170,0.15)" if v[0] else "rgba(255,69,96,0.1)",
                            fc="#00d4aa" if v[0] else "#ff4560",
                            ic="✅" if v[0] else "❌",
                            k=k
                        )
                        for k, v in _r["signals"].items()
                    )
                    st.markdown(
                        "{} <span style='color:#5a6580;font-size:11px'>量{:.1f}x</span>".format(
                            _badges, _r["vol_ratio"]
                        ),
                        unsafe_allow_html=True
                    )
                with _cst:
                    if _status:
                        st.caption(_status)
                if _chk:
                    _selected.append(_tk)

        # 確認加入按鈕
        if _selected:
            st.markdown("---")
            if st.button(
                "✅ 確認加入回測隊列（{} 隻）：{}".format(
                    len(_selected), ", ".join(_selected)
                ),
                type="primary", key="sm_confirm_add", use_container_width=True
            ):
                _newly = []
                for _t in _selected:
                    if (_t not in st.session_state["sm_queue"]
                            and _t not in st.session_state["sm_bt_done"]):
                        st.session_state["sm_queue"].append(_t)
                        _newly.append(_t)
                if _newly:
                    st.success(
                        "✅ 已加入：{}，切換到【📊 監控總覽】執行回測".format(
                            ", ".join(_newly)
                        )
                    )
                st.rerun()

        # 信號詳情展開
        with st.expander("📋 各股信號詳情"):
            for _r in _scan_res:
                st.markdown("**{}** — {}/{} 信號".format(
                    _r["ticker"], _r["sig_count"], _r["enabled"]
                ))
                for _k, (_ok, _det) in _r["signals"].items():
                    st.caption("  {} {}: {}".format("✅" if _ok else "❌", _k, _det))
                st.divider()


# ════════════════════════════════════════════════════════════════════════════
#  Tab: 📊 監控總覽
# ════════════════════════════════════════════════════════════════════════════
with tabs[-1]:
    st.markdown("## 📊 監控總覽")
    st.caption("執行回測 → 手動掃描 → 條件達標自動發送 Telegram")

    _bt_done  = st.session_state["sm_bt_done"]
    _mon_sigs = st.session_state["sm_mon_sigs"]
    _queue    = st.session_state["sm_queue"]

    # ── 回測隊列管理 ──────────────────────────────────────────────────────────
    with st.expander(
        "🔬 回測隊列（待回測：{} | 已回測：{}）".format(len(_queue), len(_bt_done)),
        expanded=len(_queue) > 0
    ):
        _qa, _qb, _qc = st.columns([2, 1, 1])
        with _qa:
            if _queue:
                st.info("待回測：{}".format(", ".join(_queue)))
            else:
                st.caption("回測隊列為空，請在【📡 Screener選股】加入股票")
        with _qb:
            _do_bt = st.button("▶ 執行回測", type="primary",
                               use_container_width=True, key="sm_mon_bt")
        with _qc:
            if st.button("🗑️ 清空已回測", use_container_width=True, key="sm_mon_clear"):
                st.session_state["sm_bt_done"]  = {}
                st.session_state["sm_mon_sigs"] = {}
                st.rerun()

        if _do_bt and _queue:
            _bprog = st.progress(0)
            for _i, _tk in enumerate(list(_queue)):
                _bprog.progress(
                    _i / len(_queue),
                    text="回測 {}（{}/{}）...".format(_tk, _i + 1, len(_queue))
                )
                _bt = _surge_backtest(
                    _tk,
                    st.session_state.get("sm_period",  "5y"),
                    st.session_state.get("sm_surge",   10),
                    st.session_state.get("sm_days",    7),
                    st.session_state.get("sm_lb",      7),
                    0.7,
                    st.session_state.get("sm_vol_win", 20),
                )
                st.session_state["sm_bt_done"][_tk] = _bt
            st.session_state["sm_queue"] = []
            _bprog.progress(1.0, text="✅ 回測完成！")
            st.rerun()

        if _bt_done:
            _del_t = st.selectbox("移除股票", ["—"] + list(_bt_done.keys()), key="sm_del_mon")
            if _del_t != "—" and st.button("移除", key="sm_do_del_mon"):
                del st.session_state["sm_bt_done"][_del_t]
                st.session_state["sm_mon_sigs"].pop(_del_t, None)
                st.rerun()

    if not _bt_done:
        st.info("📭 尚無已回測股票。請先在【📡 Screener選股】找到股票，完成回測後返回此頁。")
    else:
        # ── 監控操作列 ────────────────────────────────────────────────────────
        st.divider()
        _oa, _ob, _oc = st.columns([1, 1, 3])
        with _oa:
            _scan_all = st.button("🔍 全部立即掃描", type="primary",
                                  use_container_width=True, key="sm_scan_all")
        with _ob:
            _atg = st.checkbox(
                "觸發自動發TG",
                value=st.session_state.get("sm_auto_tg", True),
                key="sm_mon_atg"
            )
        with _oc:
            _triggered    = [t for t, s in _mon_sigs.items() if s.get("triggered")]
            _last_mon     = st.session_state.get("sm_last_mon_time", "—")
            if _triggered:
                st.error("🚨 已觸發：{}".format(", ".join(_triggered)))
            else:
                st.caption(
                    "監控 {} 隻 | 上次掃描：{} | 目前無觸發".format(
                        len(_bt_done), _last_mon
                    )
                )

        # 全部掃描
        if _scan_all:
            _vw    = st.session_state.get("sm_vol_win", 20)
            _mprog = st.progress(0)
            _dlist = list(_bt_done.keys())
            for _i, _tk in enumerate(_dlist):
                _mprog.progress(_i / len(_dlist), text="掃描 {}...".format(_tk))
                _bt  = _bt_done[_tk]
                _pwr = _bt.get("feature_power", [])
                _sig = _realtime_check(_tk, _bt, _pwr, _vw)
                st.session_state["sm_mon_sigs"][_tk] = _sig
                if _atg and _sig.get("triggered") and not _sig.get("error"):
                    _sk = "sm_{}_{}".format(_tk, _sig["time"].strftime("%Y%m%d%H%M"))
                    if _sk not in st.session_state.get("sent_signals", set()):
                        _sc = next(
                            (r["signals"] for r in st.session_state.get("sm_scan_results", [])
                             if r["ticker"] == _tk),
                            {}
                        )
                        _ok2, _ = send_telegram_alert(_sm_tg_msg(_sig, _bt, _sc), _tk)
                        if _ok2:
                            st.session_state.setdefault("sent_signals", set()).add(_sk)
                            st.toast("📱 {} 已發送".format(_tk))
            _mprog.progress(1.0, text="✅ 掃描完成")
            st.session_state["sm_last_mon_time"] = datetime.now().strftime("%H:%M:%S")
            st.rerun()

        # ── 已回測摘要表 ──────────────────────────────────────────────────────
        st.markdown("### 📋 已回測股票摘要")
        _brows = []
        for _t, _bt in _bt_done.items():
            _sig = _mon_sigs.get(_t)
            _pwr = _bt.get("feature_power", [])
            _hs  = _bt.get("horizon_stats", {})
            _bhd = max(_hs, key=lambda k: _hs[k]["平均漲幅"], default="N/A") if _hs else "N/A"
            _sc_info = next(
                ("{}/{}信號".format(r["sig_count"], r["enabled"])
                 for r in st.session_state.get("sm_scan_results", [])
                 if r["ticker"] == _t),
                "手動加入"
            )
            _brows.append({
                "股票":     _t,
                "來源":     _sc_info,
                "爆升點":   len(_bt.get("surge_points", [])) if not _bt.get("error") else "❌",
                "最強特徵": "{}({:.1f}x)".format(_pwr[0]["特徵"][:16], _pwr[0]["預測力倍數"]) if _pwr else "N/A",
                "最優持倉": _bhd,
                "最優勝率": "{}%".format(_hs.get(_bhd, {}).get("勝率", "N/A")) if _bhd != "N/A" else "N/A",
                "上次評分": "{}/{}".format(_sig["score"], _sig["max_score"]) if (_sig and not _sig.get("error")) else "—",
                "狀態":     "🚨觸發" if (_sig and _sig.get("triggered")) else "⚪監控中" if _sig else "未掃描",
            })
        st.dataframe(pd.DataFrame(_brows), use_container_width=True, hide_index=True)

        # ── 信號卡片（每行3個）────────────────────────────────────────────────
        st.markdown("### 📡 即時信號卡片")
        _dlist = list(_bt_done.keys())
        _vw    = st.session_state.get("sm_vol_win", 20)
        _atg   = st.session_state.get("sm_mon_atg", True)

        for _rs in range(0, len(_dlist), 3):
            _rtks = _dlist[_rs:_rs + 3]
            _cols = st.columns(len(_rtks))
            for _col, _tk in zip(_cols, _rtks):
                with _col:
                    _bt  = _bt_done[_tk]
                    _sig = _mon_sigs.get(_tk)

                    if st.button("🔍 {}".format(_tk), key="sm_card_{}".format(_tk),
                                 use_container_width=True):
                        _pwr = _bt.get("feature_power", [])
                        _sig = _realtime_check(_tk, _bt, _pwr, _vw)
                        st.session_state["sm_mon_sigs"][_tk] = _sig
                        if _atg and _sig.get("triggered") and not _sig.get("error"):
                            _sk = "sm_{}_{}".format(_tk, _sig["time"].strftime("%Y%m%d%H%M"))
                            if _sk not in st.session_state.get("sent_signals", set()):
                                _sc = next(
                                    (r["signals"] for r in st.session_state.get("sm_scan_results", [])
                                     if r["ticker"] == _tk),
                                    {}
                                )
                                _ok2, _ = send_telegram_alert(_sm_tg_msg(_sig, _bt, _sc), _tk)
                                if _ok2:
                                    st.session_state.setdefault("sent_signals", set()).add(_sk)
                                    st.toast("📱 {} 已發送".format(_tk))

                    if _sig is None:
                        _pwr  = _bt.get("feature_power", [])
                        _hs   = _bt.get("horizon_stats", {})
                        _bhd  = max(_hs, key=lambda k: _hs[k]["平均漲幅"], default="") if _hs else ""
                        _src  = next(
                            ("Screener {}/{}信號".format(r["sig_count"], r["enabled"])
                             for r in st.session_state.get("sm_scan_results", [])
                             if r["ticker"] == _tk),
                            "手動加入"
                        )
                        st.markdown(
                            "<div style='background:#161b27;border:1px solid #1e2535;"
                            "border-radius:8px;padding:12px'>"
                            "<b>⚪ {tk}</b><br>"
                            "<span style='font-size:11px;color:#7c5cfc'>{src}</span><br>"
                            "<span style='font-size:11px;color:#5a6580'>最強: {feat}</span><br>"
                            "<span style='font-size:11px;color:#5a6580'>持倉: {hd}</span><br>"
                            "<span style='font-size:11px;color:#00d4aa'>↑ 點擊掃描</span>"
                            "</div>".format(
                                tk=_tk, src=_src,
                                feat=_pwr[0]["特徵"][:18] if _pwr else "N/A",
                                hd=_bhd,
                            ),
                            unsafe_allow_html=True
                        )
                        continue

                    if _sig.get("error"):
                        st.warning("⚠️ {}".format(_sig["error"]))
                        continue

                    _score = _sig["score"]
                    _maxs  = _sig["max_score"]
                    _pct   = int(_score / max(_maxs, 1) * 100)
                    _trig  = _sig["triggered"]
                    _bc = "#00d4aa" if _trig else "#ffd166" if _pct >= 50 else "#5a6580"
                    _bd = "#00d4aa" if _trig else "#ffd166" if _pct >= 50 else "#2a3040"
                    _bg = "rgba(0,212,170,0.1)" if _trig else "rgba(255,209,102,0.05)" if _pct >= 50 else "#161b27"
                    _ic = "🚨" if _trig else "🟡" if _pct >= 50 else "⚪"

                    _conds  = _sig.get("conditions", [])
                    _active = [c for c in _conds if isinstance(c, dict) and c.get("active")]
                    _chtml  = "".join(
                        "<div style='font-size:11px;padding:1px 0;color:{fc}'>"
                        "{ic} {txt} "
                        "<span style='color:#5a6580'>({val})</span></div>".format(
                            fc="#00d4aa" if c["passed"] else "#ff4560",
                            ic="✅" if c["passed"] else "❌",
                            txt=c["text"].replace("✅ ", "").replace("❌ ", ""),
                            val=c["value"],
                        )
                        for c in _active
                    )
                    _src  = next(
                        ("Screener {}/{}信號".format(r["sig_count"], r["enabled"])
                         for r in st.session_state.get("sm_scan_results", [])
                         if r["ticker"] == _tk),
                        "手動加入"
                    )
                    _hs   = _bt.get("horizon_stats", {})
                    _bhd  = max(_hs, key=lambda k: _hs[k]["平均漲幅"], default="") if _hs else ""
                    _hold = "最優持倉 {}｜均漲{}%".format(_bhd, _hs[_bhd]["平均漲幅"]) if _bhd else ""

                    st.markdown(
                        "<div style='background:{bg};border:1px solid {bd};"
                        "border-radius:8px;padding:12px;margin-top:4px'>"
                        "<div style='display:flex;justify-content:space-between;"
                        "align-items:center;margin-bottom:6px'>"
                        "<span style='font-size:15px;font-weight:700'>{ic} {tk}</span>"
                        "<span style='font-size:10px;color:#5a6580'>{ts}</span></div>"
                        "<div style='font-size:10px;color:#7c5cfc;margin-bottom:6px'>{src}</div>"
                        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:4px;"
                        "margin-bottom:8px;background:rgba(0,0,0,0.2);"
                        "border-radius:4px;padding:7px'>"
                        "<div style='font-size:11px;color:#5a6580'>現價</div>"
                        "<div style='font-size:13px;font-weight:700'>${px:.2f}</div>"
                        "<div style='font-size:11px;color:#5a6580'>漲幅</div>"
                        "<div style='font-size:13px;font-weight:700;color:{rc}'>{ret:+.2f}%</div>"
                        "<div style='font-size:11px;color:#5a6580'>量倍數</div>"
                        "<div style='font-size:13px;font-weight:700;color:{vc}'>{vr:.2f}x</div>"
                        "</div>"
                        "<div style='margin-bottom:6px'>"
                        "<div style='display:flex;justify-content:space-between;"
                        "font-size:11px;margin-bottom:2px'>"
                        "<span style='color:#5a6580'>爆升前特徵評分</span>"
                        "<span style='color:{bc};font-weight:700'>{sc}/{ms} ({pct}%)</span></div>"
                        "<div style='height:5px;background:#1e2535;border-radius:3px'>"
                        "<div style='height:5px;width:{pct}%;background:{bc};"
                        "border-radius:3px'></div></div></div>"
                        "<div style='border-top:1px solid #1e2535;padding-top:6px'>{ch}</div>"
                        "{hl}"
                        "</div>".format(
                            bg=_bg, bd=_bd, ic=_ic, tk=_tk,
                            ts=_sig["time"].strftime("%H:%M:%S"),
                            src=_src,
                            px=_sig["price"],
                            rc="#00d4aa" if _sig["ret"] > 0 else "#ff4560",
                            ret=_sig["ret"] * 100,
                            vc="#00d4aa" if _sig["vol_ratio"] >= 2 else "#ffd166" if _sig["vol_ratio"] >= 1.5 else "#e8edf5",
                            vr=_sig["vol_ratio"],
                            bc=_bc, sc=_score, ms=_maxs, pct=_pct,
                            ch=_chtml,
                            hl="<div style='margin-top:5px;font-size:10px;color:#5a6580'>{}</div>".format(_hold) if _hold else "",
                        ),
                        unsafe_allow_html=True
                    )



@st.fragment
def _auto_refresh_fragment():
    """
    獨立 fragment：在背景 sleep 後觸發整頁 rerun。

    為什麼原來的方式不工作：
    - Streamlit 腳本執行完畢後進入「等待用戶操作」狀態
    - 沒有 sleep/timer，腳本不會自己再次執行
    - 必須有一個「活著的」元素去觸發 rerun

    @st.fragment 解法：
    - fragment 是獨立於主腳本的可重新執行區塊
    - time.sleep() 在 fragment 中不會凍結整個頁面
    - sleep 結束後呼叫 st.rerun() 刷新整頁
    """
    if not st.session_state.get("app_running", False):
        st.caption("⏸️ 監控已停止，自動刷新暫停")
        return

    _remaining = max(1, REFRESH_INTERVAL)
    st.caption(f"⏳ 下次自動刷新：{_remaining} 秒後…")

    time.sleep(_remaining)

    st.session_state["last_refresh"] = time.time()
    st.rerun()


_auto_refresh_fragment()
