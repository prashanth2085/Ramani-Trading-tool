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

# 1. Setup the Webpage
st.set_page_config(page_title="Ramani's Trading App", page_icon="📈", layout="wide")
st.title("📈 The Ultimate Trading Assistant")
st.write("Ramani's Core Rules + RSI + 50/200 EMA + MACD + Volume + ATR Stop-Loss")

# 2. Create the User Input Form
col1, col2, col3 = st.columns(3)
with col1:
    ticker_symbol = st.text_input("Ticker Symbol (Add .NS)", value="TATAPOWER.NS")
with col2:
    avg_price = st.number_input("Average Buy Price (₹)", value=384.75, step=1.0)
with col3:
    quantity = st.number_input("Quantity Held", value=6, step=1)

# 3. The "Analyze" Button Logic
if st.button("🔍 Analyze Live Market", type="primary"):
    with st.spinner("Fetching live data from National Stock Exchange..."):
        try:
            # Fetch 2 Years of Data (Needed for a stable 200-EMA)
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="2y")
            
            if hist.empty:
                st.error("❌ Could not find that ticker. Did you forget the '.NS'?")
            else:
                current_price = hist['Close'].iloc[-1]
                
                # --- CALCULATE INDICATORS ---
                # RSI
                hist['RSI'] = calculate_rsi(hist['Close'])
                current_rsi = hist['RSI'].iloc[-1]
                
                # EMAs
                hist['EMA_50'] = hist['Close'].ewm(span=50, adjust=False).mean()
                current_ema_50 = hist['EMA_50'].iloc[-1]
                
                hist['EMA_200'] = hist['Close'].ewm(span=200, adjust=False).mean()
                current_ema_200 = hist['EMA_200'].iloc[-1]
                
                # MACD
                macd, macd_signal = calculate_macd(hist['Close'])
                current_macd = macd.iloc[-1]
                current_signal = macd_signal.iloc[-1]
                macd_bullish = current_macd > current_signal
                
                # Volume
                hist['Avg_Vol_20'] = hist['Volume'].rolling(window=20).mean()
                current_vol = hist['Volume'].iloc[-1]
                avg_vol = hist['Avg_Vol_20'].iloc[-1]
                high_volume_dump = (current_price < hist['Open'].iloc[-1]) and (current_vol > (avg_vol * 1.5))
                
                # ATR (Stop-Loss)
                hist['ATR'] = calculate_atr(hist)
                current_atr = hist['ATR'].iloc[-1]
                auto_stop_price = avg_price - (3 * current_atr)
                auto_stop_pct = ((auto_stop_price - avg_price) / avg_price) * 100
                
                # Portfolio Math
                change_pct = ((current_price - avg_price) / avg_price) * 100
                
                # --- DISPLAY LIVE STATS ---
                st.subheader("📊 Live Technical Dashboard")
                
                # Row 1
                r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
                r1_c1.metric("Current Price", f"₹{current_price:.2f}", f"{change_pct:.2f}% from Buy")
                r1_c2.metric("Current RSI", f"{current_rsi:.2f}", "Under 40 is Cheap" if current_rsi < 40 else "Over 70 is Expensive" if current_rsi > 70 else "Neutral")
                r1_c3.metric("MACD Momentum", f"{current_macd:.2f}", "Bullish Crossover" if macd_bullish else "Bearish Momentum", delta_color="normal" if macd_bullish else "inverse")
                vol_status = "High Volatility" if current_vol > (avg_vol * 1.5) else "Normal Volume"
                r1_c4.metric("Market Volume", f"{current_vol / 1000000:.2f}M", vol_status)
                
                # Row 2
                r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
                r2_c1.metric("50-Day EMA (Medium Trend)", f"₹{current_ema_50:.2f}", "Above EMA" if current_price > current_ema_50 else "Below EMA")
                r2_c2.metric("200-Day EMA (Long Trend)", f"₹{current_ema_200:.2f}", "Bull Market" if current_price > current_ema_200 else "Bear Market")
                r2_c3.metric("Auto Stop-Loss (3x ATR)", f"₹{auto_stop_price:.2f}", f"Trigger at {auto_stop_pct:.2f}%", delta_color="inverse")
                st.divider()

                # --- MULTI-FACTOR CONFLICT RESOLUTION ---
                st.subheader("⚖️ Today's Action Plan")
                
                # 1. AUTO STOP-LOSS LOGIC
                if current_price <= auto_stop_price:
                    st.error(f"🚨 **EMERGENCY ACTION: STOP-LOSS TRIGGERED. SELL ALL {quantity} SHARES.**")
                    st.write(f"Reason: Price crashed below its natural volatility range (3x ATR). The structural trend is broken. Exit immediately.")
                
                # 2. BUY LOGIC
                elif change_pct <= -15:
                    if high_volume_dump:
                        st.error("🛑 **ACTION: DANGER - DO NOT BUY YET.**")
                        st.write("Reason: Crashing on MASSIVE volume. Big players are dumping. Wait for it to settle.")
                    
                    elif current_price < current_ema_200 and current_rsi > 30:
                        st.warning("⏸️ **ACTION: PAUSE BUY (BEAR MARKET TIER).**")
                        st.write("Reason: Stock is below the 200-Day EMA (Long-term Bear Market). RSI must drop below 30 to justify buying in a bear trend. Wait.")
                    
                    elif not macd_bullish and current_rsi > 40:
                        st.warning("⏸️ **ACTION: PAUSE BUY (NEGATIVE MOMENTUM).**")
                        st.write("Reason: Price hit your buying tier, but MACD momentum is still pointing down. Wait for momentum to flatten or turn positive.")
                        
                    else:
                        if change_pct <= -35:
                            share_pct = 0.30
                        elif change_pct <= -25:
                            share_pct = 0.25
                        else:
                            share_pct = 0.10
                            
                        qty_to_buy = max(1, int(quantity * share_pct))
                        st.success(f"✅ **ACTION: BUY {qty_to_buy} MORE SHARES.**")
                        st.write("Reason: Price hit your buying tier. Momentum (MACD) and trend support a safe entry. Perfect dip buy.")
                
                # 3. SELL LOGIC
                elif change_pct >= 25:
                    if current_rsi > 70 and current_price > (current_ema_50 * 1.15): 
                         qty_to_sell = quantity if change_pct >= 100 else max(1, int(quantity * (0.40 if change_pct >= 60 else 0.30 if change_pct >= 45 else 0.20 if change_pct >= 35 else 0.10)))
                         st.error(f"💰 **ACTION: SELL {qty_to_sell} SHARES.**")
                         st.write("Reason: Hit profit target, RSI is overbought, and price is overextended far above the 50-EMA. Lock in profit.")
                    else:
                         st.info("💎 **ACTION: HOLD YOUR WINNER.**")
                         st.write("Reason: Hit profit target, but the trend is still strong and healthy. Let your winners run.")
                
                # 4. HOLD LOGIC
                else:
                    st.info("🧘 **ACTION: HOLD PATIENTLY.**")
                    st.write("Reason: Price hasn't moved enough to trigger Ramani's rules or the ATR Stop-Loss. Ignore the market noise.")
                    
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
            st.error(f"An error occurred: {e}")
