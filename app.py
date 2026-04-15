import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- CUSTOM MATH FUNCTIONS ---
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/window, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/window, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(hist, window=14):
    high_low = hist['High'] - hist['Low']
    high_close = (hist['High'] - hist['Close'].shift()).abs()
    low_close = (hist['Low'] - hist['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(window).mean()

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

# --- PIVOT POINT CALCULATOR ---
def calculate_pivots(hist):
    # Using the previous day's High, Low, and Close to calculate today's pivot ladder
    prev_high = hist['High'].iloc[-2]
    prev_low = hist['Low'].iloc[-2]
    prev_close = hist['Close'].iloc[-2]
    
    pivot = (prev_high + prev_low + prev_close) / 3
    r1 = (pivot * 2) - prev_low
    s1 = (pivot * 2) - prev_high
    r2 = pivot + (prev_high - prev_low)
    s2 = pivot - (prev_high - prev_low)
    r3 = prev_high + 2 * (pivot - prev_low)
    s3 = prev_low - 2 * (prev_high - pivot)
    
    return pivot, s1, s2, s3, r1, r2, r3

# --- SMART DATA FETCHER ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="2y")

# 1. Setup the Webpage
st.set_page_config(page_title="Ramani's Trading App", page_icon="📈", layout="wide")
st.title("📈 The Ultimate Trading Assistant")
st.write("Portfolio Rules + Pivot Points (S1/R1) + Short/Long Trend + Technicals")

# 2. Create the User Input Form
col1, col2, col3, col4 = st.columns(4)
with col1:
    ticker_symbol = st.text_input("Ticker Symbol (Add .NS)", value="TATAPOWER.NS")
with col2:
    avg_price = st.number_input("Average Buy Price (₹)", value=384.75, step=1.0)
with col3:
    quantity = st.number_input("Quantity Held", value=6, step=1)
with col4:
    fresh_capital = st.number_input("Fresh Capital Available (₹)", value=10000, step=1000)

# 3. The "Analyze" Button Logic
if st.button("🔍 Analyze Live Market", type="primary"):
    with st.spinner("Fetching live data from National Stock Exchange..."):
        try:
            hist = fetch_stock_data(ticker_symbol)
            
            if len(hist) < 200:
                st.error("❌ Not enough data found for this ticker.")
            else:
                current_price = hist['Close'].iloc[-1]
                
                # --- CALCULATE INDICATORS ---
                hist['RSI'] = calculate_rsi(hist['Close'])
                current_rsi = hist['RSI'].iloc[-1]
                
                # Short Term Trend (5 & 20 SMA)
                hist['SMA_5'] = hist['Close'].rolling(window=5).mean()
                hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
                short_term_bullish = hist['SMA_5'].iloc[-1] > hist['SMA_20'].iloc[-1]
                
                # Long Term Trend (50 & 200 EMA)
                hist['EMA_50'] = hist['Close'].ewm(span=50, adjust=False).mean()
                hist['EMA_200'] = hist['Close'].ewm(span=200, adjust=False).mean()
                long_term_bullish = current_price > hist['EMA_200'].iloc[-1]
                
                macd, macd_signal = calculate_macd(hist['Close'])
                macd_bullish = macd.iloc[-1] > macd_signal.iloc[-1]
                
                hist['Avg_Vol_20'] = hist['Volume'].rolling(window=20).mean()
                current_vol = hist['Volume'].iloc[-1]
                high_volume_dump = (current_price < hist['Open'].iloc[-1]) and (current_vol > (hist['Avg_Vol_20'].iloc[-1] * 1.5))
                
                hist['ATR'] = calculate_atr(hist)
                auto_stop_price = avg_price - (3 * hist['ATR'].iloc[-1])
                auto_stop_pct = ((auto_stop_price - avg_price) / avg_price) * 100
                
                # Pivot Points
                pivot, s1, s2, s3, r1, r2, r3 = calculate_pivots(hist)
                
                change_pct = ((current_price - avg_price) / avg_price) * 100
                affordable_shares = int(fresh_capital / current_price) if current_price > 0 else 0
                
                # --- DISPLAY LIVE STATS ---
                st.subheader("📊 Live Technical Dashboard")
                
                # Row 1: Core
                r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
                r1_c1.metric("Current Price", f"₹{current_price:.2f}", f"{change_pct:.2f}% from Buy")
                r1_c2.metric("Current RSI", f"{current_rsi:.2f}", "Neutral" if 40 <= current_rsi <= 70 else "Oversold/Cheap" if current_rsi < 40 else "Overbought/Expensive")
                r1_c3.metric("Short Term (5/20 SMA)", "Bullish Cross" if short_term_bullish else "Bearish Cross", delta_color="normal" if short_term_bullish else "inverse")
                r1_c4.metric("Long Term (50/200 EMA)", "Bull Market" if long_term_bullish else "Bear Market", delta_color="normal" if long_term_bullish else "inverse")
                
                # Row 2: Pivot Points (The Ladder)
                st.write("**Today's Pivot Levels (Support & Resistance Ladder)**")
                p_c1, p_c2, p_c3, p_c4, p_c5, p_c6, p_c7 = st.columns(7)
                p_c1.metric("S3 (Crash Floor)", f"₹{s3:.0f}")
                p_c2.metric("S2", f"₹{s2:.0f}")
                p_c3.metric("S1 (Support)", f"₹{s1:.0f}")
                p_c4.metric("PIVOT (Center)", f"₹{pivot:.0f}")
                p_c5.metric("R1 (Resistance)", f"₹{r1:.0f}")
                p_c6.metric("R2", f"₹{r2:.0f}")
                p_c7.metric("R3 (Breakout)", f"₹{r3:.0f}")
                st.divider()

                # --- FRESH CAPITAL OPPORTUNITIES ---
                st.subheader("💡 Fresh Capital Opportunities")
                st.write(f"*Deploying your ₹{fresh_capital} budget using Pivot Points & Trend.*")
                
                if not long_term_bullish:
                    st.error("🛑 **AVOID FRESH ENTRIES.**")
                    st.write("The stock is in a macro bear market (Below 200-EMA). Keep your cash safe until the structural trend reverses.")
                elif current_price < s1 and short_term_bullish and macd_bullish:
                    st.success(f"🎯 **PRIME DIP BUY: {affordable_shares} SHARES.**")
                    st.write(f"Price is down near S1/S2 support levels, but Short-Term momentum just flashed Bullish. This is a sniper entry opportunity.")
                elif current_price > r1 and not short_term_bullish:
                    st.warning("⚠️ **REJECTED AT RESISTANCE. DO NOT BUY.**")
                    st.write("The stock is hitting the R1/R2 ceiling and losing short-term momentum. Wait for a pullback to the Pivot or S1.")
                elif short_term_bullish:
                    st.info(f"📈 **TRENDING UP: SAFE TO SCALp {affordable_shares} SHARES.**")
                    st.write("The stock is between Pivot and R1 with strong momentum. It is safe to ride the wave upward.")
                else:
                    st.info("⏳ **WAITING FOR A SETUP.**")
                    st.write("The stock is floating between levels with no clear short-term momentum. Keep your cash in the bank for now.")
                
                st.divider()

                # --- ORIGINAL SECTION: RAMANI'S ACTION PLAN ---
                st.subheader("⚖️ Ramani's Action Plan")
                st.write(f"*Managing your existing {quantity} shares based on your average buy price.*")
                
                if current_price <= auto_stop_price:
                    st.error(f"🚨 **EMERGENCY ACTION: STOP-LOSS TRIGGERED. SELL ALL {quantity} SHARES.**")
                elif change_pct <= -15:
                    if high_volume_dump:
                        st.error("🛑 **ACTION: DANGER - DO NOT BUY YET.**")
                    elif not long_term_bullish and current_rsi > 30:
                        st.warning("⏸️ **ACTION: PAUSE BUY (BEAR MARKET TIER).**")
                    elif not macd_bullish and current_rsi > 40:
                        st.warning("⏸️ **ACTION: PAUSE BUY (NEGATIVE MOMENTUM).**")
                    else:
                        share_pct = 0.30 if change_pct <= -35 else 0.25 if change_pct <= -25 else 0.10
                        qty_to_buy = max(1, int(quantity * share_pct))
                        st.success(f"✅ **ACTION: BUY {qty_to_buy} MORE SHARES.** (Ramani Dip Buy)")
                elif change_pct >= 25:
                    if current_rsi > 70 and current_price > (hist['EMA_50'].iloc[-1] * 1.15): 
                         share_pct = 1.0 if change_pct >= 100 else 0.40 if change_pct >= 60 else 0.30 if change_pct >= 45 else 0.20 if change_pct >= 35 else 0.10
                         qty_to_sell = max(1, int(quantity * share_pct))
                         st.error(f"💰 **ACTION: SELL {qty_to_sell} SHARES.** (Ramani Profit Taking)")
                    else:
                         st.info("💎 **ACTION: HOLD YOUR WINNER.**")
                else:
                    st.info("🧘 **ACTION: HOLD PATIENTLY.**")
                    
                st.divider()
                
                # --- FUTURE TARGETS (CHEAT SHEET) ---
                st.subheader("🎯 Future Price Targets & Trades")
                rules = [
                    {"pct": auto_stop_pct, "action": "🚨 AUTO STOP-LOSS", "share_pct": 100},
                    {"pct": -35, "action": "Buy", "share_pct": 30},
                    {"pct": -25, "action": "Buy", "share_pct": 25},
                    {"pct": -15, "action": "Buy", "share_pct": 10},
                    {"pct": 25, "action": "Sell", "share_pct": 10},
                    {"pct": 35, "action": "Sell", "share_pct": 20},
                    {"pct": 45, "action": "Sell", "share_pct": 30},
                    {"pct": 60, "action": "Sell", "share_pct": 40},
                    {"pct": 100, "action": "Sell", "share_pct": 100}
                ]
                
                target_data = []
                for r in rules:
                    if r["pct"] > auto_stop_pct or "STOP-LOSS" in r["action"]:
                        target_price = avg_price * (1 + (r["pct"]/100))
                        trade_qty = max(1, int(quantity * (r["share_pct"]/100)))
                        target_data.append({
                            "Trigger Level (%)": f"{'+' if r['pct']>0 else ''}{r['pct']:.2f}%",
                            "Target Price (₹)": f"₹{target_price:.2f}",
                            "Action": r["action"],
                            "Shares to Trade": f"{quantity} shares" if "STOP-LOSS" in r["action"] else f"{trade_qty} shares"
                        })
                
                st.table(pd.DataFrame(target_data).sort_values(by="Trigger Level (%)", key=lambda col: col.str.replace('+','').str.replace('%','').astype(float)))

        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                st.error("⚠️ Yahoo Finance is rate-limiting. Please wait a few minutes.")
            else:
                st.error(f"An error occurred: {e}")
