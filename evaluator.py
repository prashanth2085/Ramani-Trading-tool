import pandas as pd
import numpy as np
import requests

class StockEvaluator:
    def __init__(self, ticker, avg_price, purchase_date):
        self.ticker = ticker
        self.avg_price = avg_price
        self.purchase_date = purchase_date
        self.data = self._get_data()

    def _get_data(self):
        try:
            # --- THE ULTIMATE RATE-LIMIT BYPASS ---
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{self.ticker}"
            params = {"interval": "1d", "range": "2y"}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]
            
            df = pd.DataFrame({
                "Close": quote["close"],
                "High": quote["high"],
                "Low": quote["low"]
            }, index=pd.to_datetime(timestamps, unit="s"))
            
            return df.dropna()
            
        except Exception as e:
            print(f"Data fetch error: {e}")
            return pd.DataFrame()

    def calculate_technicals(self):
        df = self.data.copy()
        
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        last_day = df.iloc[-2] 
        current_price = float(df['Close'].iloc[-1])
        
        high = float(last_day['High'])
        low = float(last_day['Low'])
        close = float(last_day['Close'])
        
        # --- CALCULATE FULL PIVOT LADDER ---
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        
        # --- DYNAMIC TARGET & ENTRY LOGIC ---
        # If the stock is breaking out, the targets shift UP automatically.
        if current_price > r2:
            target = r3
            entry = r2
            stop = r1
        elif current_price > r1:
            target = r2
            entry = r1
            stop = pivot
        elif current_price > pivot:
            target = r1
            entry = pivot
            stop = s1
        else:
            target = pivot
            entry = s1
            stop = s2
            
        return {
            "current_price": current_price,
            "sma200": float(df['SMA200'].iloc[-1]) if not pd.isna(df['SMA200'].iloc[-1]) else 0.0,
            "rsi": float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0,
            "dynamic_target": target,
            "dynamic_entry": entry,
            "dynamic_stop": stop,
            "p": pivot  # Keeping this for the score logic below
        }

    def evaluate(self):
        if self.data.empty or len(self.data) < 200:
            return {"Error": "Not enough data fetched to evaluate. Check the ticker symbol or try again."}
            
        tech = self.calculate_technicals()
        price = tech['current_price']
        sma = tech['sma200']
        rsi = tech['rsi']
        
        p_l_pct = ((price - self.avg_price) / self.avg_price) * 100
        
        score = 0
        recom = "HOLD"
        
        if price > sma and sma > 0: score += 40  
        if rsi < 70: score += 30                 
        if price > tech['p']: score += 30        
        
        if score >= 80 and p_l_pct < 0:
            recom = "BUY / ACCUMULATE"
        elif score < 40:
            recom = "SELL / REDUCE"
            
        return {
            "Ticker": self.ticker,
            "Current Price": round(price, 2),
            "P/L %": f"{round(p_l_pct, 2)}%",
            "Institutional Trend": "Bullish" if price > sma else "Bearish",
            "RSI Status": "Overbought" if rsi > 70 else "Neutral/Oversold",
            "Recommendation": recom,
            "Confidence": f"{score}%",
            "Target Price": round(tech['dynamic_target'], 2),
            "Stop Loss": round(tech['dynamic_stop'], 2),
            "Recommended Price": round(tech['dynamic_entry'], 2)
        }

if __name__ == "__main__":
    evaluator = StockEvaluator("OLECTRA.NS", 1600, "2024-06-04")
    print(evaluator.evaluate())
