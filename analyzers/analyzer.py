import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

with open(os.path.join(ROOT, "profiles", "wind_turbine.json"), encoding="utf-8") as f:
    profile = json.load(f)
with open(os.path.join(HERE, "knowledge.json"), encoding="utf-8") as f:
    knowledge = json.load(f)


def analyze(reading):
    symptoms = []
    overall = "normal"

    for name, p in profile["parameters"].items():
        value = reading.get(name)
        if value is None:
            continue

        if value >= p["critical_high"]:
            status = "critical"
        elif value >= p["warning_high"]:
            status = "warning"
        else:
            status = "normal"

        if status != "normal":
            symptoms.append({
                "parameter": name,
                "label": p["label"],
                "value": value,
                "unit": p["unit"],
                "status": status,
            })
            if status == "critical" or overall == "normal":
                overall = status

    return {"status": overall, "symptoms": symptoms}


def diagnose(symptoms):
    active = {s["parameter"] for s in symptoms}
    candidates = []

    for fault in knowledge["faults"]:
        matched = [p for p in fault["symptoms"] if p in active]
        if not matched:
            continue
        candidates.append({
            "id": fault["id"],
            "name": fault["name"],
            "confidence": round(len(matched) / len(fault["symptoms"]) * 100),
            "matched": matched,
            "causes": fault["causes"],
            "checks": fault["checks"],
            "severity": fault["severity"],
        })

    # more matched symptoms first, then higher confidence
    candidates.sort(key=lambda c: (len(c["matched"]), c["confidence"]), reverse=True)
    return candidates


def full_analysis(reading):
    result = analyze(reading)
    result["diagnoses"] = diagnose(result["symptoms"])
    return result


if __name__ == "__main__":
    tests = {
        "normal":    {"gearbox_oil_temp": 55, "vibration": 1.2},
        "gearbox":   {"gearbox_oil_temp": 85, "gearbox_bearing_temp": 90},
        "vibration": {"vibration": 5.0},
    }
    for name, reading in tests.items():
        result = full_analysis(reading)
        print(name, "->", result["status"])
        if not result["diagnoses"]:
            print("    no fault")
        for d in result["diagnoses"]:
            print(f"    {d['name']} ({d['confidence']}%)")