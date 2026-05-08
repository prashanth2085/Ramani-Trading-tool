import yfinance as yf
import pandas as pd
import numpy as np

class StockEvaluator:
    def __init__(self, ticker, avg_price, purchase_date):
        self.ticker = ticker
        self.avg_price = avg_price
        self.purchase_date = purchase_date
        self.data = self._get_data()

    def _get_data(self):
        # Fetch data from purchase date to today
        df = yf.download(self.ticker, start=self.purchase_date)
        return df

    def calculate_technicals(self):
        df = self.data.copy()
        
        # 200-Day Simple Moving Average
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        
        # Relative Strength Index (RSI)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Pivot Points (Standard)
        last_day = df.iloc[-2] # Use previous day for pivot calculation
        high, low, close = last_day['High'], last_day['Low'], last_day['Close']
        
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        
        return {
            "current_price": df['Close'].iloc[-1],
            "sma200": df['SMA200'].iloc[-1],
            "rsi": df['RSI'].iloc[-1],
            "p": pivot,
            "r1": r1,
            "s1": s1
        }

    def evaluate(self):
        tech = self.calculate_technicals()
        price = tech['current_price']
        sma = tech['sma200']
        rsi = tech['rsi']
        
        p_l_pct = ((price - self.avg_price) / self.avg_price) * 100
        
        # Recommendation Logic
        score = 0
        recom = "HOLD"
        
        if price > sma: score += 40  # Institutional Bullish
        if rsi < 70: score += 30    # Not Overbought
        if price > tech['p']: score += 30 # Above Pivot
        
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
            "Confidence": f"{score}%"
        }

# Usage
evaluator = StockEvaluator("OLECTRA.NS", 1600, "2024-06-04")
print(evaluator.evaluate())
