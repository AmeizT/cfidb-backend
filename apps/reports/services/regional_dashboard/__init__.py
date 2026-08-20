from .compliance import build_region_compliance_module
from .finance import build_region_finance_module
from .growth import build_region_growth_module
from .leadership import build_region_leadership_module
from .ministry import build_region_ministry_module
from .overview import build_region_overview
from .risk import build_region_risk_module

__all__ = [
    "build_region_compliance_module",
    "build_region_finance_module",
    "build_region_growth_module",
    "build_region_leadership_module",
    "build_region_ministry_module",
    "build_region_overview",
    "build_region_risk_module",
]
