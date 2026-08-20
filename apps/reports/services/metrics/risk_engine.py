# from dataclasses import dataclass


# # -----------------------------
# # RISK LEVELS
# # -----------------------------
# def get_risk_level(score):
#     if score >= 75:
#         return "CRITICAL"
#     if score >= 50:
#         return "HIGH"
#     if score >= 25:
#         return "MEDIUM"
#     return "LOW"


# # -----------------------------
# # 1. COMPLIANCE RISK
# # -----------------------------
# def calculate_compliance_risk(compliance):
#     if not compliance:
#         return 40, "NO DATA AVAILABLE"

#     skipped = compliance.get("skipped", 0)
#     pending = compliance.get("pending", 0)

#     score = (skipped * 10) + (pending * 15)

#     reason = f"{skipped} skipped, {pending} pending sections"

#     return min(score, 40), reason


# # -----------------------------
# # 2. FINANCE RISK
# # -----------------------------
# def calculate_finance_risk(finance):
#     if not finance:
#         return 30, "NO FINANCIAL DATA"

#     balance = finance.get("balance", 0)
#     income = finance.get("income", 0)

#     score = 0
#     reasons = []

#     if balance < 0:
#         score += 30
#         reasons.append("Negative balance")

#     if income == 0:
#         score += 20
#         reasons.append("No income")

#     return min(score, 30), ", ".join(reasons) if reasons else "Stable finances"


# # -----------------------------
# # 3. GROWTH RISK
# # -----------------------------
# def calculate_growth_risk(growth):
#     if not growth:
#         return 20, "NO GROWTH DATA"

#     new_members = growth.get("new_members", 0)

#     score = 0
#     reasons = []

#     if new_members == 0:
#         score += 15
#         reasons.append("No new members")

#     return min(score, 20), ", ".join(reasons) if reasons else "Stable growth"


# # -----------------------------
# # 4. ASSEMBLY RISK (MAIN ENTRY)
# # -----------------------------
# def calculate_assembly_risk(assembly_data):
#     compliance = assembly_data.get("compliance", {})
#     finance = assembly_data.get("metrics", {}).get("finance", {})
#     growth = assembly_data.get("metrics", {}).get("growth", {})

#     comp_score, comp_reason = calculate_compliance_risk(compliance)
#     fin_score, fin_reason = calculate_finance_risk(finance)
#     growth_score, growth_reason = calculate_growth_risk(growth)

#     total_score = comp_score + fin_score + growth_score
#     total_score = min(total_score, 100)

#     return {
#         "risk_score": total_score,
#         "risk_level": get_risk_level(total_score),
#         "factors": [
#             {"type": "COMPLIANCE", "score": comp_score, "reason": comp_reason},
#             {"type": "FINANCE", "score": fin_score, "reason": fin_reason},
#             {"type": "GROWTH", "score": growth_score, "reason": growth_reason},
#         ],
#     }




from typing import Any


def get_risk_level(score: int) -> str:
    if score <= 20:
        return "LOW"

    if score <= 50:
        return "MEDIUM"

    if score <= 75:
        return "HIGH"

    return "CRITICAL"


def calculate_risk(
    compliance: dict[str, Any],
    finance: dict[str, Any],
    growth: dict[str, Any],
    ministry: dict[str, Any],
    *,
    previous_score: int | None = None,
) -> dict[str, Any]:

    compliance_factor = 0
    finance_factor = 0
    growth_factor = 0
    ministry_factor = 0

    coverage = compliance.get("coverage", 0)

    if coverage < 25:
        compliance_factor = 40
    elif coverage < 50:
        compliance_factor = 30
    elif coverage < 75:
        compliance_factor = 20
    elif coverage < 100:
        compliance_factor = 10

    finance_status = finance.get("status")

    if finance_status == "TIGHT":
        finance_factor = 15

    elif finance_status == "DEFICIT":
        finance_factor = 30

    growth_status = growth.get("status")

    if growth_status == "SLOW":
        growth_factor = 10

    elif growth_status == "STAGNANT":
        growth_factor = 20

    ministry_status = ministry.get("status")

    if ministry_status == "MODERATE":
        ministry_factor = 5

    elif ministry_status == "LOW":
        ministry_factor = 10

    score = compliance_factor + finance_factor + growth_factor + ministry_factor

    result: dict[str, Any] = {
        "score": score,
        "level": get_risk_level(score),
        "factors": {
            "compliance_factor": compliance_factor,
            "financial_factor": finance_factor,
            "growth_factor": growth_factor,
            "ministry_factor": ministry_factor,
        },
    }

    if previous_score is not None:
        if score > previous_score:
            result["trend"] = "WORSENING"
        elif score < previous_score:
            result["trend"] = "IMPROVING"
        else:
            result["trend"] = "STABLE"

    return result
