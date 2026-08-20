from .finance_metrics import get_finance_metrics
from .growth_metrics import get_growth_metrics
from .ministry_metrics import get_ministry_metrics
from .leadership_metrics import get_leadership_metrics


def get_assembly_dashboard(report):
    return {
        "finance": get_finance_metrics(report),
        "growth": get_growth_metrics(report),
        "ministry": get_ministry_metrics(report),
        "leadership": get_leadership_metrics(report),
    }