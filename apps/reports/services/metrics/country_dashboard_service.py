def build_country_dashboard(country, assemblies):
    return {
        "country": country,
        "assemblies": [
            {
                "id": assembly.id,
                "name": assembly.name,
                "reports": len(reports),
            }
            for assembly, reports in assemblies
        ]
    }