import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

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

# --- SMART DATA FETCHER (BYPASSES RATE LIMITS) ---
@st.cache_data(ttl=300, show_spinner=False) # Caches data for 5 minutes to prevent spamming Yahoo
def fetch_stock_data(symbol):
    # Disguise the request as a normal web browser
    session = requests.Session()
    session.headers.update(
        {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
    )
    ticker = yf.Ticker(symbol, session=session)
    return ticker.history(period="2y")

# 1. Setup the Webpage
st.set_page_config(page_title="Ramani's Trading App", page_icon="📈", layout="wide")
st.title("📈 The Ultimate Trading Assistant")
st.write("Portfolio Rules + Market Structure (Support/Resistance) + Technicals")

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
            # Use our new cached and disguised fetcher
            hist = fetch_stock_data(ticker_symbol)
            
            if hist.empty:
                st.error("❌ Could not find that ticker. Did you forget the '.NS'?")
            else:
                current_price = hist['Close'].iloc[-1]
                
                # --- CALCULATE INDICATORS ---
                hist['RSI'] = calculate_rsi(hist['Close'])
                current_rsi = hist['RSI'].iloc[-1]
                
                hist['EMA_50'] = hist['Close'].ewm(span=50, adjust=False).mean()
                current_ema_50 = hist['EMA_50'].iloc[-1]
                hist['EMA_200'] = hist['Close'].ewm(span=200, adjust=False).mean()
                current_ema_200 = hist['EMA_200'].iloc[-1]
                
                macd, macd_signal = calculate_macd(hist['Close'])
                current_macd = macd.iloc[-1]
                current_signal = macd_signal.iloc[-1]
                macd_bullish = current_macd > current_signal
                
                hist['Avg_Vol_20'] = hist['Volume'].rolling(window=20).mean()
                current_vol = hist['Volume'].iloc[-1]
                avg_vol = hist['Avg_Vol_20'].iloc[-1]
                high_volume_dump = (current_price < hist['Open'].iloc[-1]) and (current_vol > (avg_vol * 1.5))
                
                hist['ATR'] = calculate_atr(hist)
                current_atr = hist['ATR'].iloc[-1]
                auto_stop_price = avg_price - (3 * current_atr)
                auto_stop_pct = ((auto_stop_price - avg_price) / avg_price) * 100
                
                hist['Support_20'] = hist['Low'].rolling(window=20).min()
                hist['Resistance_20'] = hist['High'].rolling(window=20).max()
                current_support = hist['Support_20'].iloc[-1]
                current_resistance = hist['Resistance_20'].iloc[-1]
                
                change_pct = ((current_price - avg_price) / avg_price) * 100
                affordable_shares = int(fresh_capital / current_price) if current_price > 0 else 0
                
                # --- DISPLAY LIVE STATS ---
                st.subheader("📊 Live Technical Dashboard")
                
                r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
                r1_c1.metric("Current Price", f"₹{current_price:.2f}", f"{change_pct:.2f}% from Buy")
                r1_c2.metric("Current RSI", f"{current_rsi:.2f}", "Under 40 is Cheap" if current_rsi < 40 else "Over 70 is Expensive" if current_rsi > 70 else "Neutral")
                r1_c3.metric("MACD Momentum", f"{current_macd:.2f}", "Bullish" if macd_bullish else "Bearish", delta_color="normal" if macd_bullish else "inverse")
                r1_c4.metric("Market Volume", f"{current_vol / 1000000:.2f}M", "High Volatility" if current_vol > (avg_vol * 1.5) else "Normal Volume")
                
                r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
                r2_c1.metric("50-Day EMA (Medium Trend)", f"₹{current_ema_50:.2f}", "Above EMA" if current_price > current_ema_50 else "Below EMA")
                r2_c2.metric("200-Day EMA (Long Trend)", f"₹{current_ema_200:.2f}", "Bull Market" if current_price > current_ema_200 else "Bear Market")
                r2_c3.metric("20-Day Support (Floor)", f"₹{current_support:.2f}")
                r2_c4.metric("20-Day Resistance (Ceiling)", f"₹{current_resistance:.2f}")
                st.divider()

                # --- FRESH CAPITAL OPPORTUNITIES ---
                st.subheader("💡 Fresh Capital Opportunities (Market-Anchored)")
                st.write(f"*Deploying your ₹{fresh_capital} budget based on today's market structure.*")
                
                distance_to_support = ((current_price - current_support) / current_support) * 100
                distance_to_resistance = ((current_resistance - current_price) / current_price) * 100
                
                if current_price < current_ema_200:
                    st.error("🛑 **AVOID FRESH ENTRIES.**")
                    st.write("The stock is in a long-term bear market (Below 200-EMA). Keep your cash safe until the structural trend reverses.")
                elif distance_to_support <= 2.0:
                    if macd_bullish:
                        st.success(f"🎯 **PRIME ENTRY ZONE: BUY {affordable_shares} SHARES.**")
                        st.write(f"The stock is resting perfectly on its Support floor (₹{current_support:.2f}) and momentum is bullish. You can afford {affordable_shares} shares. High-probability entry.")
                    else:
                        st.warning("⚠️ **AT SUPPORT, BUT MOMENTUM IS WEAK.**")
                        st.write(f"The stock is at Support (₹{current_support:.2f}), but MACD is bearish. Watch closely. If it bounces, buy {affordable_shares} shares. If it breaks below Support, wait.")
                elif distance_to_resistance <= 2.0:
                    st.warning("⚠️ **AVOID ENTRY (NEAR RESISTANCE).**")
                    st.write(f"The stock is hitting its historical ceiling (₹{current_resistance:.2f}). It is likely to be rejected. Wait for a pullback to support before deploying cash.")
                else:
                    st.info("⏳ **NO MAN'S LAND. WAIT.**")
                    st.write(f"The stock is floating between Support (₹{current_support:.2f}) and Resistance (₹{current_resistance:.2f}). No clear edge right now. Wait for it to drop closer to Support.")
                
                st.divider()

                # --- ORIGINAL SECTION: RAMANI'S ACTION PLAN ---
                st.subheader("⚖️ Ramani's Action Plan (Portfolio-Anchored)")
                st.write(f"*Managing your existing {quantity} shares based on your average buy price.*")
                
                if current_price <= auto_stop_price:
                    st.error(f"🚨 **EMERGENCY ACTION: STOP-LOSS TRIGGERED. SELL ALL {quantity} SHARES.**")
                elif change_pct <= -15:
                    if high_volume_dump:
                        st.error("🛑 **ACTION: DANGER - DO NOT BUY YET.**")
                    elif current_price < current_ema_200 and current_rsi > 30:
                        st.warning("⏸️ **ACTION: PAUSE BUY (BEAR MARKET TIER).**")
                    elif not macd_bullish and current_rsi > 40:
                        st.warning("⏸️ **ACTION: PAUSE BUY (NEGATIVE MOMENTUM).**")
                    else:
                        share_pct = 0.30 if change_pct <= -35 else 0.25 if change_pct <= -25 else 0.10
                        qty_to_buy = max(1, int(quantity * share_pct))
                        st.success(f"✅ **ACTION: BUY {qty_to_buy} MORE SHARES.** (Ramani Dip Buy)")
                elif change_pct >= 25:
                    if current_rsi > 70 and current_price > (current_ema_50 * 1.15): 
                         share_pct = 1.0 if change_pct >= 100 else 0.40 if change_pct >= 60 else 0.30 if change_pct >= 45 else 0.20 if change_pct >= 35 else 0.10
                         qty_to_sell = max(1, int(quantity * share_pct))
                         st.error(f"💰 **ACTION: SELL {qty_to_sell} SHARES.** (Ramani Profit Taking)")
                    else:
                         st.info("💎 **ACTION: HOLD YOUR WINNER.**")
                else:
                    st.info("🧘 **ACTION: HOLD PATIENTLY.** (In the middle zone).")
                    
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
            # We catch rate limits specifically to give a friendlier message
            if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                st.error("⚠️ Yahoo Finance is temporarily blocking requests due to high traffic. The app's new caching system will help prevent this, but please wait 2-3 minutes before trying again.")
            else:
                st.error(f"An error occurred: {e}")
