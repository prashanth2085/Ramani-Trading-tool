import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random

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

def calculate_pivots(hist):
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

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="2y")

# 1. Setup the Webpage
st.set_page_config(page_title="Ramani's Trading App", page_icon="📈", layout="wide")
st.title("📈 The Ultimate Trading Assistant")
st.write("Ramani's Core Engine | RSI + MACD + Volume + Pivot Structure")
st.divider()

# 2. Create the User Input Form (WITH THE NEW TOGGLE SWITCH)
trade_mode = st.radio("🎯 Select Dashboard Mode:", ["Manage Existing Portfolio", "Scout New Trade"], horizontal=True)

col1, col2, col3 = st.columns(3)

with col1:
    ticker_symbol = st.text_input("Ticker Symbol (Add .NS for India)", value="TATAPOWER.NS")

# Dynamic inputs based on the toggle switch
if trade_mode == "Manage Existing Portfolio":
    with col2:
        avg_price = st.number_input("Average Buy Price (₹/$)", value=384.75, step=1.0)
    with col3:
        quantity = st.number_input("Quantity Held", value=6, step=1)
    fresh_capital = 0 # Not needed for this mode
    trade_horizon = "N/A"
else:
    with col2:
        fresh_capital = st.number_input("Investment Budget (₹/$)", value=5000.0, step=500.0)
    with col3:
        trade_horizon = st.selectbox("Trade Horizon", ["Short-Term (Swing/Scalp)", "Long-Term (Growth)"])
    avg_price = 0 # Not needed for this mode
    quantity = 0

st.write("<br>", unsafe_allow_html=True)

# 3. The "Analyze" Button Logic
if st.button("🔍 Analyze Live Market", type="primary"):
    with st.spinner("Fetching live data..."):
        try:
            hist = fetch_stock_data(ticker_symbol)
            
            if len(hist) < 200:
                st.error("❌ Not enough data found for this ticker.")
            else:
                current_price = hist['Close'].iloc[-1]
                
                # --- CALCULATE ALL INDICATORS ---
                hist['RSI'] = calculate_rsi(hist['Close'])
                current_rsi = hist['RSI'].iloc[-1]
                
                hist['SMA_5'] = hist['Close'].rolling(window=5).mean()
                hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
                short_term_bullish = hist['SMA_5'].iloc[-1] > hist['SMA_20'].iloc[-1]
                
                hist['EMA_50'] = hist['Close'].ewm(span=50, adjust=False).mean()
                current_ema_50 = hist['EMA_50'].iloc[-1]
                
                hist['EMA_200'] = hist['Close'].ewm(span=200, adjust=False).mean()
                current_ema_200 = hist['EMA_200'].iloc[-1]
                long_term_bullish = current_price > current_ema_200
                
                macd, macd_signal = calculate_macd(hist['Close'])
                current_macd = macd.iloc[-1]
                macd_bullish = current_macd > macd_signal.iloc[-1]
                
                hist['Avg_Vol_20'] = hist['Volume'].rolling(window=20).mean()
                current_vol = hist['Volume'].iloc[-1]
                avg_vol = hist['Avg_Vol_20'].iloc[-1]
                
                hist['ATR'] = calculate_atr(hist)
                current_atr = hist['ATR'].iloc[-1]
                
                # Base price depends on mode
                base_price = avg_price if trade_mode == "Manage Existing Portfolio" else current_price
                    
                auto_stop_price = base_price - (3 * current_atr)
                auto_stop_pct = ((auto_stop_price - base_price) / base_price) * 100
                
                pivot, s1, s2, s3, r1, r2, r3 = calculate_pivots(hist)
                
                change_pct = ((current_price - base_price) / base_price) * 100
                affordable_shares = int(fresh_capital / current_price) if current_price > 0 else 0
                
                # --- DISPLAY LIVE STATS ---
                st.subheader("📊 Live Technical Dashboard")
                
                r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
                r1_c1.metric("Current Price", f"{current_price:.2f}", f"{change_pct:.2f}% from Base" if trade_mode == "Manage Existing Portfolio" else "Live")
                r1_c2.metric("Current RSI", f"{current_rsi:.2f}", "Neutral" if 40 <= current_rsi <= 70 else "Oversold/Cheap" if current_rsi < 40 else "Overbought/Expensive")
                r1_c3.metric("MACD Momentum", f"{current_macd:.2f}", "Bullish" if macd_bullish else "Bearish", delta_color="normal" if macd_bullish else "inverse")
                r1_c4.metric("Market Volume", f"{current_vol / 1000000:.2f}M", "High Volatility" if current_vol > (avg_vol * 1.5) else "Normal Volume")
                
                r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
                r2_c1.metric("50-Day EMA", f"{current_ema_50:.2f}", "Above EMA" if current_price > current_ema_50 else "Below EMA")
                r2_c2.metric("200-Day EMA", f"{current_ema_200:.2f}", "Bull Market" if long_term_bullish else "Bear Market")
                r2_c3.metric("Short Term (5/20)", "Bullish Cross" if short_term_bullish else "Bearish Cross", delta_color="normal" if short_term_bullish else "inverse")
                r2_c4.metric("Stop-Loss (3x ATR)", f"{auto_stop_price:.2f}", f"Trigger at {auto_stop_pct:.2f}%", delta_color="inverse")
                
                st.divider()

                # --- VISUAL PIVOT LADDER (PLOTLY) ---
                st.write("**📍 Today's Pivot Levels (Support & Resistance Ladder)**")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=[s3, r3], y=[0, 0], mode="lines", line=dict(color="gray", width=5), showlegend=False))
                levels = [s3, s2, s1, pivot, r1, r2, r3]
                labels = [f"S3<br>{s3:.0f}", f"S2<br>{s2:.0f}", f"S1<br>{s1:.0f}", f"PIVOT<br>{pivot:.0f}", f"R1<br>{r1:.0f}", f"R2<br>{r2:.0f}", f"R3<br>{r3:.0f}"]
                colors = ["#8B0000", "#FF4500", "#FFA07A", "gray", "#90EE90", "#32CD32", "#006400"] 
                fig.add_trace(go.Scatter(x=levels, y=[0]*7, mode="markers+text", marker=dict(color=colors, size=20), text=labels, textposition="top center", showlegend=False))
                fig.add_trace(go.Scatter(x=[current_price], y=[0], mode="markers+text", marker=dict(color="#00BFFF", size=24, symbol="diamond", line=dict(color='white', width=2)), text=[f"CURRENT<br>{current_price:.2f}"], textposition="bottom center", showlegend=False))
                fig.update_layout(xaxis=dict(showgrid=False, zeroline=False, visible=False, range=[s3*0.95, r3*1.05]), yaxis=dict(showgrid=False, zeroline=False, visible=False, range=[-1, 1]), height=200, margin=dict(l=20, r=20, t=40, b=40), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                st.divider()

                # --- CONDITIONAL DISPLAY ---
                
                if trade_mode == "Scout New Trade":
                    st.subheader("🚀 New Trade Blueprint")
                    st.write(f"*Evaluating this stock for a **{trade_horizon}** investment.*")
                    
                    if not long_term_bullish and trade_horizon == "Long-Term (Growth)":
                        st.error("🛑 **VERDICT: AVOID FOR LONG-TERM.**")
                        st.write("This stock is in a macro bear market (Below 200-EMA). Do not invest long-term capital here until the structural trend reverses.")
                    elif current_rsi > 70:
                        st.warning("⚠️ **VERDICT: WAIT FOR PULLBACK.**")
                        st.write("The stock is currently overbought. Wait for the price to cool down towards the Pivot or S1 Support before entering.")
                    elif current_price <= pivot and short_term_bullish:
                        st.success(f"🎯 **VERDICT: PRIME ENTRY. BUY {affordable_shares} SHARES.**")
                        st.write("Price is near Support with Bullish momentum. Excellent risk-to-reward ratio.")
                    else:
                        st.info(f"📈 **VERDICT: ACCEPTABLE ENTRY.**")
                        st.write("The trend is up, but you are buying midway between Support and Resistance. Proceed with standard caution.")
                    
                    st.write("### 📋 Your Trade Execution Plan")
                    
                    # Tailor targets based on Short vs Long term
                    if trade_horizon == "Short-Term (Swing/Scalp)":
                        target_price = r1
                        target_reason = "(R1 Resistance Level)"
                    else:
                        target_price = current_price * 1.25 # Defaulting to Ramani's +25% rule for long term
                        target_reason = "(+25% Macro Target)"

                    plan_data = [
                        {"Step": "1. Entry Strategy", "Details": f"Buy {affordable_shares} shares at/near {current_price:.2f}"},
                        {"Step": "2. Hard Stop-Loss", "Details": f"Sell everything if price closes below {auto_stop_price:.2f} (ATR Floor)"},
                        {"Step": f"3. Target Exit", "Details": f"Take profits near {target_price:.2f} {target_reason}"}
                    ]
                    st.table(pd.DataFrame(plan_data))
                    
                else:
                    st.subheader("⚖️ Ramani's Action Plan")
                    st.write(f"*Managing your existing {quantity} shares based on your average buy price.*")
                    
                    if current_price <= auto_stop_price:
                        st.error(f"🚨 **EMERGENCY ACTION: STOP-LOSS TRIGGERED. SELL ALL {quantity} SHARES.**")
                    elif change_pct <= -15:
                        if not long_term_bullish and current_rsi > 30:
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
                                "Target Price": f"{target_price:.2f}",
                                "Action": r["action"],
                                "Shares to Trade": f"{quantity} shares" if "STOP-LOSS" in r["action"] else f"{trade_qty} shares"
                            })
                    
                    st.table(pd.DataFrame(target_data).sort_values(by="Trigger Level (%)", key=lambda col: col.str.replace('+','').str.replace('%','').astype(float)))

        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                st.error("⚠️ Yahoo Finance is rate-limiting. Please wait a few minutes.")
            else:
                st.error(f"An error occurred: {e}")

# --- MOTIVATIONAL FOOTER ---
st.write("<br><br>", unsafe_allow_html=True)
quotes = [
    "\"The elements of good trading are (1) cutting losses, (2) cutting losses, and (3) cutting losses.\" – Ed Seykota",
    "\"If you cannot control your emotions, you cannot control your money.\" – Warren Buffett",
    "\"Plan your trade and trade your plan. Trust the math, not your gut.\"",
    "\"Novices focus on what they can make. Professionals focus on what they can lose.\"",
    "\"Do not anticipate and move without market confirmation. Being a little late in your trade is your insurance.\" – Jesse Livermore",
    "\"Let your winners run, and cut your losses quickly.\"",
    "\"The goal of a successful trader is to make the best trades. Money is secondary.\" – Alexander Elder",
    "\"Amateurs want to be right. Professionals want to make money.\""
]
st.markdown(f"> *{random.choice(quotes)}*")
