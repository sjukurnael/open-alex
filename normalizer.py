"""
normalizer.py — Maps raw ClinicalTrials.gov API study dicts to a flat schema.
"""


def normalize(raw: dict) -> dict:
    protocol = raw.get("protocolSection", {})
    derived = raw.get("derivedSection", {})

    identification = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    interventions_module = protocol.get("armsInterventionsModule", {})
    eligibility = protocol.get("eligibilityModule", {})
    locations_module = protocol.get("contactsLocationsModule", {})

    condition_browse = derived.get("conditionBrowseModule", {})
    intervention_browse = derived.get("interventionBrowseModule", {})

    nct_id = identification.get("nctId", "")

    # phases — already a list in the raw data
    phases = design.get("phases", [])

    # interventions — list of {type, name}
    raw_interventions = interventions_module.get("interventions", [])
    interventions = [
        {
            "type": iv.get("type", ""),
            "name": iv.get("name", ""),
        }
        for iv in raw_interventions
    ]

    # mesh terms
    mesh_terms = [
        m.get("term", "")
        for m in condition_browse.get("meshes", [])
    ]
    drug_mesh_terms = [
        m.get("term", "")
        for m in intervention_browse.get("meshes", [])
    ]

    # countries — unique values from locations list
    locations = locations_module.get("locations", [])
    countries = list({loc.get("country", "") for loc in locations if loc.get("country")})

    # enrollment
    enrollment_info = design.get("enrollmentInfo", {})
    try:
        enrollment = int(enrollment_info.get("count", 0) or 0)
    except (ValueError, TypeError):
        enrollment = 0

    # sponsor
    lead_sponsor = sponsor_module.get("leadSponsor", {})

    return {
        "nct_id": nct_id,
        "brief_title": identification.get("briefTitle", ""),
        "official_title": identification.get("officialTitle", ""),
        "status": status_module.get("overallStatus", ""),
        "study_type": design.get("studyType", ""),
        "phases": phases,
        "start_date": status_module.get("startDateStruct", {}).get("date", ""),
        "completion_date": status_module.get("completionDateStruct", {}).get("date", ""),
        "last_updated": status_module.get("lastUpdatePostDateStruct", {}).get("date", ""),
        "sponsor": lead_sponsor.get("name", ""),
        "sponsor_class": lead_sponsor.get("class", ""),
        "conditions": conditions_module.get("conditions", []),
        "interventions": interventions,
        "mesh_terms": mesh_terms,
        "drug_mesh_terms": drug_mesh_terms,
        "countries": countries,
        "enrollment": enrollment,
        "sex": eligibility.get("sex", ""),
        "min_age": eligibility.get("minimumAge", ""),
        "max_age": eligibility.get("maximumAge", ""),
        "has_results": raw.get("hasResults", False),
        "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
    }


# ---------------------------------------------------------------------------
# Quick test — fetch 5 real trials and pretty-print normalized output
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    from fetcher import fetch_trials

    print("Fetching 5 trials for normalization test …\n")
    raw_trials = fetch_trials(since_date="2026-02-20")
    sample = raw_trials[:5]

    for i, raw in enumerate(sample, 1):
        normalized = normalize(raw)
        print(f"--- Trial {i} ---")
        print(json.dumps(normalized, indent=2))
        print()
