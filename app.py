import streamlit as st
import yfinance as yf
import pandas_ta as ta

# 1. Setup the Webpage
st.set_page_config(page_title="Dad's Trading App", page_icon="📈")
st.title("📈 Dad's Live Trading Assistant")
st.write("Enter your stock details below to get your live recommendation.")

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
            # Fetch Data
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="60d")
            
            if hist.empty:
                st.error("❌ Could not find that ticker. Did you forget the '.NS'?")
            else:
                current_price = hist['Close'].iloc[-1]
                
                # Calculate RSI
                hist.ta.rsi(length=14, append=True)
                current_rsi = hist['RSI_14'].iloc[-1]
                
                # Calculate Percentage Change
                change_pct = ((current_price - avg_price) / avg_price) * 100
                
                # 4. Display Live Stats nicely
                st.subheader("📊 Live Market Stats")
                stat1, stat2, stat3 = st.columns(3)
                stat1.metric("Current Price", f"₹{current_price:.2f}")
                stat2.metric("Change from Buy Price", f"{change_pct:.2f}%")
                stat3.metric("Current RSI", f"{current_rsi:.2f}")
                
                st.write("*(Note: RSI under 40 is Cheap/Oversold. RSI over 70 is Expensive/Overbought)*")
                st.divider()

                # 5. Dad's Rules & Conflict Resolution
                st.subheader("⚖️ Dad's Rule Decision")
                
                if change_pct <= -15:
                    if current_rsi < 40:
                        qty_to_buy = max(1, int(quantity * 0.10))
                        st.success(f"✅ **ACTION: BUY {qty_to_buy} MORE SHARES.**")
                        st.write("Reason: Price dropped 15%+ AND Technicals show it is cheap (RSI low).")
                    else:
                        st.warning("⏸️ **ACTION: PAUSE BUY.**")
                        st.write("Reason: Price dropped 15%, but Technicals show it might fall further (RSI too high). Wait.")
                
                elif change_pct >= 25:
                    if current_rsi > 70:
                         qty_to_sell = max(1, int(quantity * 0.10))
                         st.error(f"💰 **ACTION: SELL {qty_to_sell} SHARES.**")
                         st.write("Reason: Price is up 25%+ AND Technicals show it is currently overvalued (RSI high). Lock in profit.")
                    else:
                         st.info("💎 **ACTION: HOLD YOUR WINNER.**")
                         st.write("Reason: Price is up 25%+, but the trend is still strong (RSI healthy). Let it grow.")
                
                else:
                    st.info("🧘 **ACTION: HOLD PATIENTLY.**")
                    st.write("Reason: Price hasn't moved enough to trigger a buy or sell rule.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
