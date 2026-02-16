"""
使用示例 - 展示如何使用交易平台
"""
import asyncio
from core.scheduler import TradingPlatformScheduler
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)


async def example_basic_usage():
    """基本使用示例"""
    print("\n" + "="*60)
    print("AI Agent Stock Trading Platform - 基本使用示例")
    print("="*60 + "\n")
    
    # 1. 创建调度器
    print("1. 创建交易平台调度器...")
    scheduler = TradingPlatformScheduler()
    
    # 2. 添加股票
    print("\n2. 添加股票到监控列表...")
    stocks = ["AAPL", "NVDA", "MSFT"]
    for stock in stocks:
        scheduler.add_stock(stock)
        print(f"   - 已添加: {stock}")
    
    # 3. 查看系统状态
    print("\n3. 系统状态:")
    status = await get_system_status(scheduler)
    print(f"   - 运行状态: {status['is_running']}")
    print(f"   - 监控股票数: {status['active_stocks']}")
    
    # 4. 手动运行一次分析（模拟）
    print("\n4. 手动运行分析...")
    
    # 运行D1宏观分析
    print("   - 运行D1宏观分析...")
    await scheduler._run_d1()
    
    # 运行D7选股
    print("   - 运行D7选股...")
    await scheduler._run_d7()
    
    # 为每只股票运行分析
    for symbol in stocks:
        print(f"   - 分析 {symbol}...")
        await scheduler._run_d2(symbol)
        await scheduler._run_d3(symbol)
        await scheduler._run_d5(symbol)
    
    # 5. 查看分析结果
    print("\n5. 分析结果:")
    for symbol in stocks:
        analysis = scheduler.get_stock_analysis(symbol)
        if analysis:
            print(f"\n   {symbol}:")
            dept_finals = analysis.get('department_finals', {})
            for dept, final in dept_finals.items():
                print(f"     {dept}: 分数={final.get('score', 0):.2f}, "
                      f"置信度={final.get('confidence', 0):.2f}")
            
            quant = analysis.get('quant_output')
            if quant:
                print(f"     量化建议: alpha={quant.get('final_alpha', 0):.4f}, "
                      f"仓位={quant.get('position', 0):.2f}")
    
    # 6. 查看账户状态
    print("\n6. 账户状态:")
    account = scheduler.get_account_status()
    print(f"   - 总资产: ${account['total_value']:,.2f}")
    print(f"   - 现金: ${account['cash']:,.2f}")
    print(f"   - 总盈亏: ${account['total_pnl']:,.2f}")
    
    print("\n" + "="*60)
    print("示例完成!")
    print("="*60 + "\n")


async def get_system_status(scheduler):
    """获取系统状态"""
    return {
        'is_running': scheduler.state.is_running,
        'active_stocks': len(scheduler.state.active_stocks),
        'last_run_times': scheduler.state.last_run_times
    }


async def example_custom_material():
    """自定义材料上传示例"""
    print("\n" + "="*60)
    print("上传专家材料示例")
    print("="*60 + "\n")
    
    scheduler = TradingPlatformScheduler()
    scheduler.add_stock("AAPL")
    
    # 上传专家材料
    from models.base_models import Evidence
    
    material = Evidence(
        content="根据最新分析，苹果公司新产品发布将推动股价上涨10-15%",
        timestamp=datetime.now(),
        source_id="expert_analysis_001",
        reliability_score=0.85,
        summary="专家看多苹果"
    )
    
    scheduler.d4.upload_material(material)
    print("已上传专家材料")
    
    # 运行D4分析
    await scheduler._run_d4("AAPL")
    
    # 查看结果
    analysis = scheduler.get_stock_analysis("AAPL")
    if 'D4' in analysis.get('department_finals', {}):
        d4_final = analysis['department_finals']['D4']
        print(f"D4分析结果: 分数={d4_final['score']:.2f}, "
              f"置信度={d4_final['confidence']:.2f}")


async def example_evaluation():
    """评估示例"""
    print("\n" + "="*60)
    print("评估系统示例")
    print("="*60 + "\n")
    
    from utils.evaluation import EvaluationEngine
    
    eval_engine = EvaluationEngine()
    
    # 模拟多个案例评估
    cases = [
        {
            'case_id': 'case_001',
            'symbol': 'AAPL',
            'created_at': datetime.now().isoformat(),
            'trading_decision': {'direction': 'LONG'},
            'quant_output': {'divergence': 0.2},
            'department_finals': {'D6': {'confidence': 0.8, 'score': 0.6}}
        },
        {
            'case_id': 'case_002',
            'symbol': 'NVDA',
            'created_at': datetime.now().isoformat(),
            'trading_decision': {'direction': 'LONG'},
            'quant_output': {'divergence': 0.3},
            'department_finals': {'D6': {'confidence': 0.7, 'score': 0.5}}
        }
    ]
    
    returns = [0.05, -0.02]  # 实际收益率
    
    for case, ret in zip(cases, returns):
        evaluation = eval_engine.evaluate_case(case, ret)
        print(f"案例 {case['case_id']}: "
              f"决策={case['trading_decision']['direction']}, "
              f"收益={ret*100:.1f}%, "
              f"命中={evaluation.hit}")
    
    # 生成报告
    report = eval_engine.generate_report()
    print(f"\n评估报告:")
    print(f"  总交易次数: {report['metrics']['total_trades']}")
    print(f"  胜率: {report['metrics']['win_rate']*100:.1f}%")
    print(f"  总收益: {report['metrics']['total_return']*100:.1f}%")


async def main():
    """主函数"""
    await example_basic_usage()
    await example_custom_material()
    await example_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
