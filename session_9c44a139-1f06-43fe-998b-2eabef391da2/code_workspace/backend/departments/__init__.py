"""Departments package"""
from .base_department import BaseDepartment
from .d1_macro import D1MacroDepartment
from .d2_industry import D2IndustryDepartment
from .d3_stock import D3StockDepartment
from .d4_expert import D4ExpertDepartment
from .d6_ic import D6ICDepartment
from .d7_stock_selection import D7StockSelectionDepartment, StockCandidate

__all__ = [
    'BaseDepartment', 'D1MacroDepartment', 'D2IndustryDepartment',
    'D3StockDepartment', 'D4ExpertDepartment', 'D6ICDepartment',
    'D7StockSelectionDepartment', 'StockCandidate'
]
