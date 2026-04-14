import streamlit as st
import yfinance as yf
import pandas as pd

# --- CUSTOM MATH FUNCTIONS ---
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/window, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/window, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 1. Setup the Webpage
st.set_page_config(page_title="Ramani's Trading App", page_icon="📈", layout="wide")
st.title("📈 The Ultimate Trading Assistant")
st.write("Ramani's Core Rules + RSI + EMA + Volume Analysis")

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
            # Fetch 1 Year of Data (Needed for 50-EMA)
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                st.error("❌ Could not find that ticker. Did you forget the '.NS'?")
            else:
                # --- CALCULATE ALL INDICATORS ---
                current_price = hist['Close'].iloc[-1]
                
                # RSI
                hist['RSI'] = calculate_rsi(hist['Close'])
                current_rsi = hist['RSI'].iloc[-1]
                
                # 50-Day EMA
                hist['EMA_50'] = hist['Close'].ewm(span=50, adjust=False).mean()
                current_ema = hist['EMA_50'].iloc[-1]
                
                # Volume Analysis (Compare today to 20-day average)
                hist['Avg_Vol_20'] = hist['Volume'].rolling(window=20).mean()
                current_vol = hist['Volume'].iloc[-1]
                avg_vol = hist['Avg_Vol_20'].iloc[-1]
                high_volume_dump = (current_price < hist['Open'].iloc[-1]) and (current_vol > (avg_vol * 1.5))
                
                # Ramani's % Change
                change_pct = ((current_price - avg_price) / avg_price) * 100
                
                # --- DISPLAY LIVE STATS ---
                st.subheader("📊 Live Technical Dashboard")
                stat1, stat2, stat3, stat4 = st.columns(4)
                stat1.metric("Current Price", f"₹{current_price:.2f}", f"{change_pct:.2f}% from Buy")
                stat2.metric("Current RSI", f"{current_rsi:.2f}", "Under 40 is Cheap" if current_rsi < 40 else "Over 70 is Expensive" if current_rsi > 70 else "Neutral")
                stat3.metric("50-Day EMA", f"₹{current_ema:.2f}", "Bullish Trend" if current_price > current_ema else "Bearish Trend")
                
                vol_status = "High Volatility" if current_vol > (avg_vol * 1.5) else "Normal Volume"
                stat4.metric("Market Volume", f"{current_vol / 1000000:.2f}M", vol_status)
                st.divider()

                # --- MULTI-FACTOR CONFLICT RESOLUTION ---
                st.subheader("⚖️ Today's Action Plan")
                
                # BUY LOGIC
                if change_pct <= -15:
                    if high_volume_dump:
                        st.error("🛑 **ACTION: DANGER - DO NOT BUY YET.**")
                        st.write("Reason: Price dropped 15%, but it is crashing on MASSIVE volume. Big players are dumping. Wait for it to settle.")
                    elif current_rsi > 50 and current_price < current_ema:
                        st.warning("⏸️ **ACTION: PAUSE BUY.**")
                        st.write("Reason: Price dropped 15%, but the trend is broken (below 50-EMA) and RSI isn't cheap enough yet. Wait.")
                    else:
                        qty_to_buy = max(1, int(quantity * (0.25 if change_pct <= -25 else 0.10)))
                        st.success(f"✅ **ACTION: BUY {qty_to_buy} MORE SHARES.**")
                        st.write("Reason: Price dropped to your buying tier, RSI shows it is oversold, and volume is safe. Perfect dip buy.")
                
                # SELL LOGIC
                elif change_pct >= 25:
                    if current_rsi > 70 and current_price > (current_ema * 1.15): # 15% extended from EMA
                         qty_to_sell = quantity if change_pct >= 100 else max(1, int(quantity * (0.40 if change_pct >= 60 else 0.30 if change_pct >= 45 else 0.20 if change_pct >= 35 else 0.10)))
                         st.error(f"💰 **ACTION: SELL {qty_to_sell} SHARES.**")
                         st.write("Reason: Hit profit target, RSI is overbought, and price is overextended far above the 50-EMA. Lock in profit.")
                    else:
                         st.info("💎 **ACTION: HOLD YOUR WINNER.**")
                         st.write("Reason: Hit profit target, but the trend is still strong and healthy. Let your winners run.")
                
                # HOLD LOGIC
                else:
                    st.info("🧘 **ACTION: HOLD PATIENTLY.**")
                    st.write("Reason: Price hasn't moved enough to trigger Ramani's rules. Ignore the market noise.")
                    
                st.divider()
                
                # --- FUTURE TARGETS (CHEAT SHEET) ---
                st.subheader("🎯 Future Price Targets & Trades")
                rules = [
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
                    target_price = avg_price * (1 + (r["pct"]/100))
                    trade_qty = max(1, int(quantity * (r["share_pct"]/100)))
                    target_data.append({
                        "Trigger Level (%)": f"{'+' if r['pct']>0 else ''}{r['pct']}%",
                        "Target Price (₹)": f"₹{target_price:.2f}",
                        "Action": r["action"],
                        "Shares to Trade": f"{trade_qty} shares"
                    })
                
                st.table(pd.DataFrame(target_data))

        except Exception as e:
            st.error(f"An error occurred: {e}")
