# Windows & macOS 快速部署指南

## 1. 克隆项目
```bash
git clone https://github.com/BruceLZX/miniQUANT.git
cd miniQUANT
```

## 2. 创建Python虚拟环境
### macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
### Windows:
```cmd
python -m venv .venv
.venv\Scripts\activate
```

## 3. 安装依赖
```bash
pip install -r requirements.txt
```

## 4. 运行示例策略与回测
```bash
python backtest/simple_backtest.py
```

---

- 推荐使用Python 3.8及以上版本
- 如需安装Jupyter Notebook：
  ```bash
  pip install notebook
  ```
- 如遇依赖问题，优先升级pip：
  ```bash
  python -m pip install --upgrade pip
  ```

## 目录说明
- `strategies/` 策略示例
- `data/` 数据样例
- `backtest/` 回测脚本
- `notebooks/` 交互式学习

---

如有问题欢迎提issue！
