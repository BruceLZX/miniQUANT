# 示例动量策略

import pandas as pd

def momentum_strategy(data: pd.DataFrame, window: int = 20):
    data['momentum'] = data['close'].diff(window)
    data['signal'] = 0
    data.loc[data['momentum'] > 0, 'signal'] = 1
    data.loc[data['momentum'] <= 0, 'signal'] = -1
    return data

# 示例用法
if __name__ == "__main__":
    # 假设有data.csv，包含close列
    df = pd.read_csv('../data/data.csv')
    result = momentum_strategy(df)
    print(result[['close', 'momentum', 'signal']].tail())
