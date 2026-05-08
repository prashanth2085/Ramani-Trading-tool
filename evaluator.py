import yfinance as yf
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
            # --- ANTI-RATE-LIMIT DISGUISE ---
            # Tricking Yahoo into thinking we are a normal Chrome browser
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            ticker_obj = yf.Ticker(self.ticker, session=session)
            df = ticker_obj.history(start=self.purchase_date)
            return df
        except Exception as e:
            # If Yahoo rate-limits us, return an empty dataframe safely
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
        
        high = float(last_day['High'])
        low = float(last_day['Low'])
        close = float(last_day['Close'])
        
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        
        return {
            "current_price": float(df['Close'].iloc[-1]),
            "sma200": float(df['SMA200'].iloc[-1]) if not pd.isna(df['SMA200'].iloc[-1]) else 0.0,
            "rsi": float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0,
            "p": pivot,
            "r1": r1,
            "s1": s1
        }

    def evaluate(self):
        if self.data.empty or len(self.data) < 2:
            return {"Error": "Not enough data fetched to evaluate. Yahoo Finance may be rate-limiting your connection. Please wait a few minutes and try again."}
            
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
            "Target Price": round(tech['r1'], 2),
            "Stop Loss": round(tech['s1'], 2),
            "Recommended Price": round(tech['p'], 2)
        }

if __name__ == "__main__":
    evaluator = StockEvaluator("OLECTRA.NS", 1600, "2024-06-04")
    print(evaluator.evaluate())
