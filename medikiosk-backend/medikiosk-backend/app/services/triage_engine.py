"""
Rule-based triage engine — this is REAL, working logic (not mocked).

Deliberately deterministic and explainable rather than a black-box ML
model: every flag traces to a specific vital crossing a specific published
clinical threshold, and `rationale` explains each flag in plain language.
This mirrors the design principle already used in `summary.py`/`ontology.py`
(LLMs are for phrasing, not decisions) — here, no LLM is involved in the
risk decision at all; only the threshold table in core/config.py is.

Thresholds are simplified for screening/flagging purposes only — this is a
pre-consultation triage aid, not a diagnostic tool, and every output should
be read that way (see `recommended_action` on the critical/high paths).
"""
from dataclasses import dataclass, field

from app.core.config import get_settings

settings = get_settings()
T = settings.TRIAGE_THRESHOLDS

RISK_ORDER = ["low", "moderate", "high", "critical"]


@dataclass
class TriageOutcome:
    risk_level: str = "low"
    flags: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    recommended_action: str = "No immediate concerns from vitals. Proceed with routine intake."

    def escalate(self, level: str, flag: str, reason: str):
        self.flags.append(flag)
        self.rationale.append(reason)
        if RISK_ORDER.index(level) > RISK_ORDER.index(self.risk_level):
            self.risk_level = level


def run_triage(vitals: dict, known_conditions: list[str] | None = None) -> TriageOutcome:
    """
    `vitals` accepts the same keys as VitalsIn: systolic_bp, diastolic_bp,
    heart_rate_bpm, spo2_percent, temperature_c, glucose_mg_dl,
    glucose_context. Missing values are simply skipped — this is a
    screening pass over whatever was actually measured.

    `known_conditions` — condition names extracted from the patient's past
    documents (see services/document_ocr.py), e.g. ["Diabetes",
    "Hypertension"]. When a flag corresponds to an already-known condition,
    the rationale is reworded to say so ("known diabetic — monitoring
    trend" rather than sounding like a brand-new finding) — the risk level
    itself is unchanged; this only affects how the flag is explained.
    """
    outcome = TriageOutcome()
    known = {c.lower() for c in (known_conditions or [])}

    def note(condition_name: str, new_reason: str, known_reason: str) -> str:
        return known_reason if condition_name.lower() in known else new_reason

    systolic = vitals.get("systolic_bp")
    diastolic = vitals.get("diastolic_bp")
    if systolic is not None and diastolic is not None:
        if systolic >= T["systolic_bp_crisis"] or diastolic >= T["diastolic_bp_crisis"]:
            outcome.escalate(
                "critical", "hypertensive_crisis",
                f"Blood pressure {systolic:.0f}/{diastolic:.0f} mmHg is in the hypertensive crisis range "
                f"(\u2265{T['systolic_bp_crisis']}/{T['diastolic_bp_crisis']})."
            )
        elif systolic >= T["systolic_bp_high"] or diastolic >= T["diastolic_bp_high"]:
            outcome.escalate(
                "high", "hypertension",
                note(
                    "Hypertension",
                    f"Blood pressure {systolic:.0f}/{diastolic:.0f} mmHg exceeds the high-BP threshold "
                    f"(\u2265{T['systolic_bp_high']}/{T['diastolic_bp_high']}).",
                    f"Blood pressure {systolic:.0f}/{diastolic:.0f} mmHg is elevated — patient has a known "
                    f"history of hypertension, recommend reviewing trend with current medication.",
                )
            )

    spo2 = vitals.get("spo2_percent")
    if spo2 is not None:
        if spo2 < T["spo2_critical"]:
            outcome.escalate(
                "critical", "severe_hypoxia",
                f"SpO2 {spo2:.0f}% is below the critical threshold ({T['spo2_critical']}%) — indicates severe hypoxia."
            )
        elif spo2 < T["spo2_low"]:
            outcome.escalate(
                "high", "hypoxia",
                f"SpO2 {spo2:.0f}% is below normal ({T['spo2_low']}%)."
            )

    hr = vitals.get("heart_rate_bpm")
    if hr is not None:
        if hr > T["heart_rate_high"]:
            outcome.escalate(
                "moderate", "tachycardia",
                f"Heart rate {hr:.0f} bpm is above normal resting range (>{T['heart_rate_high']})."
            )
        elif hr < T["heart_rate_low"]:
            outcome.escalate(
                "moderate", "bradycardia",
                f"Heart rate {hr:.0f} bpm is below normal resting range (<{T['heart_rate_low']})."
            )

    temp = vitals.get("temperature_c")
    if temp is not None:
        if temp >= T["temp_high_fever_c"]:
            outcome.escalate(
                "high", "high_fever",
                f"Temperature {temp:.1f}\u00b0C indicates a high fever (\u2265{T['temp_high_fever_c']}\u00b0C)."
            )
        elif temp >= T["temp_fever_c"]:
            outcome.escalate(
                "moderate", "fever",
                f"Temperature {temp:.1f}\u00b0C indicates a fever (\u2265{T['temp_fever_c']}\u00b0C)."
            )

    glucose = vitals.get("glucose_mg_dl")
    glucose_context = vitals.get("glucose_context") or "random"
    if glucose is not None:
        if glucose < T["glucose_low"]:
            outcome.escalate(
                "high", "hypoglycemia",
                f"Blood glucose {glucose:.0f} mg/dL is below normal ({T['glucose_low']}) — risk of hypoglycemia."
            )
        elif glucose_context == "fasting" and glucose >= T["glucose_fasting_high"]:
            outcome.escalate(
                "moderate", "hyperglycemia_fasting",
                note(
                    "Diabetes",
                    f"Fasting glucose {glucose:.0f} mg/dL is above the diabetes screening threshold "
                    f"(\u2265{T['glucose_fasting_high']}).",
                    f"Fasting glucose {glucose:.0f} mg/dL — patient has a known history of diabetes, "
                    f"recommend reviewing control/medication adherence rather than new screening.",
                )
            )
        elif glucose_context != "fasting" and glucose >= T["glucose_random_high"]:
            outcome.escalate(
                "moderate", "hyperglycemia_random",
                f"Random glucose {glucose:.0f} mg/dL is above the diabetes screening threshold "
                f"(\u2265{T['glucose_random_high']})."
            )

    # Combination rule: fever + low SpO2 together warrants a bump even if
    # neither alone hit "high" — a common respiratory-infection pattern.
    if temp is not None and spo2 is not None:
        if temp >= T["temp_fever_c"] and spo2 < T["spo2_low"] and outcome.risk_level not in ("high", "critical"):
            outcome.escalate(
                "high", "febrile_hypoxia_pattern",
                "Fever combined with reduced oxygen saturation together suggest a possible respiratory infection "
                "warranting closer review."
            )

    outcome.recommended_action = _recommended_action(outcome.risk_level)
    return outcome


def _recommended_action(risk_level: str) -> str:
    return {
        "low": "No immediate concerns from vitals. Proceed with routine intake.",
        "moderate": "Flag for doctor review during today's consultation; not an emergency.",
        "high": "Prioritize this patient for the next available doctor consultation.",
        "critical": "Escalate immediately — connect to a doctor now or advise nearest facility referral.",
    }[risk_level]
