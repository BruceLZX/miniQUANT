# 简单回测框架
import pandas as pd

def backtest(data: pd.DataFrame):
    data['return'] = data['close'].pct_change()
    data['strategy_return'] = data['return'] * data['signal'].shift(1)
    data['equity_curve'] = (1 + data['strategy_return']).cumprod()
    return data

if __name__ == "__main__":
    df = pd.read_csv('../data/data.csv')
    from strategies.momentum import momentum_strategy
    df = momentum_strategy(df)
    result = backtest(df)
    print(result[['close', 'signal', 'equity_curve']].tail())
