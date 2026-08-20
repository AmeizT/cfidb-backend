from apps.reports.models.alerts import ComplianceAlert


def generate_alerts(metrics, assembly, zone=None):
    alerts = []

    # 🔴 CRITICAL RISK
    if metrics["risk_level"] == "CRITICAL":
        alerts.append(
            ComplianceAlert(
                assembly=assembly,
                zone=zone,
                type=ComplianceAlert.Type.RISK,
                level=ComplianceAlert.Level.CRITICAL,
                title="Critical Compliance Risk",
                message="Assembly is in critical compliance state and requires immediate attention.",
                metadata=metrics,
            )
        )

    # 🟠 DECLINING TREND
    if metrics["trend"] == "DECLINING":
        alerts.append(
            ComplianceAlert(
                assembly=assembly,
                zone=zone,
                type=ComplianceAlert.Type.TREND,
                level=ComplianceAlert.Level.HIGH,
                title="Declining Performance Trend",
                message="Performance has declined over recent months.",
                metadata=metrics,
            )
        )

    # ⚠️ HIGH SKIP RATE
    if metrics.get("skip_rate", 0) > 30:
        alerts.append(
            ComplianceAlert(
                assembly=assembly,
                zone=zone,
                type=ComplianceAlert.Type.SKIP_PATTERN,
                level=ComplianceAlert.Level.MEDIUM,
                title="High Skip Rate Detected",
                message="Repeated section skipping detected.",
                metadata=metrics,
            )
        )

    return alerts