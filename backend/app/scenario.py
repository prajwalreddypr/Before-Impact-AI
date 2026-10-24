COEFFICIENTS = {
    "greenhouse": 0.42, "warehouse": 0.24, "crop": 0.5, "inventory": 0.36,
    "machinery": 0.3, "electrical": 0.48, "water": 0.2, "road": 0.12,
    "building": 0.22, "equipment": 0.32,
}


def calculate_exposure(assets, event, selected_action_ids):
    selected = len(set(selected_action_ids or []))
    severity = {"wind": 0.78, "rain": 0.58, "flood": 0.82, "heat": 0.66, "wildfire": 0.76, "drought": 0.61}.get(event.hazard_type, 0.5)
    protection = min(0.48, selected * 0.09)
    rows, low, high = [], 0.0, 0.0
    for asset in assets:
        coefficient = COEFFICIENTS.get(asset.asset_type, COEFFICIENTS.get("equipment"))
        exposure = max(0.04, min(1.0, severity * coefficient * (1 - protection)))
        asset_low = round(asset.value_amount * exposure * 0.55, -1)
        asset_high = round(asset.value_amount * exposure * 1.15, -1)
        low += asset_low
        high += asset_high
        rows.append({"asset_id": asset.id, "name": asset.name, "exposure_score": round(exposure * 100),
                     "risk": "high" if exposure >= .32 else "medium" if exposure >= .16 else "low",
                     "loss_range": [asset_low, asset_high]})
    return {
        "model_version": "exposure-1.0", "illustrative": True,
        "hazard": event.hazard_type, "severity_index": severity,
        "protection_modifier": round(protection, 2), "actions_applied": selected,
        "exposure_score": round(sum(r["exposure_score"] for r in rows) / max(1, len(rows))),
        "potential_loss_range": [round(low, -2), round(high, -2)], "assets": rows,
        "limitations": "Educational exposure estimate, not an engineering, insurance, or safety assessment."
    }
