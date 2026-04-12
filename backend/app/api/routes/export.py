"""HL7 FHIR R4 export route — DiagnosticReport for HIS/EMR integration."""
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["export"])

LOINC_CT_HEAD = {"system": "http://loinc.org", "code": "24627-2", "display": "CT Head"}
SNOMED_HEMORRHAGE = {"system": "http://snomed.info/sct", "code": "274100004", "display": "Cerebral hemorrhage"}
SNOMED_NO_FINDING = {"system": "http://snomed.info/sct", "code": "281296001", "display": "No finding"}

HEMORRHAGE_SNOMED = {
    "epidural": {"code": "712832005", "display": "Epidural hematoma"},
    "intraparenchymal": {"code": "274100004", "display": "Intraparenchymal hemorrhage"},
    "intraventricular": {"code": "95457006", "display": "Intraventricular hemorrhage"},
    "subarachnoid": {"code": "21454007", "display": "Subarachnoid hemorrhage"},
    "subdural": {"code": "35486000", "display": "Subdural hematoma"},
    "any": {"code": "274100004", "display": "Intracranial hemorrhage"},
}


class HL7ExportRequest(BaseModel):
    hospital: str
    top_class: str
    confidence: float
    probabilities: Dict[str, float]
    filename: Optional[str] = None
    radiologist_verdict: Optional[str] = None  # confirm | reject | correct
    corrected_class: Optional[str] = None
    slice_used: Optional[int] = None
    model_type: Optional[str] = "hybrid"


class HL7ExportResponse(BaseModel):
    fhir_json: dict
    resource_id: str


def _build_observation(code: str, display: str, probability: float, threshold_met: bool) -> dict:
    return {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": code, "display": display}],
            "text": display,
        },
        "valueQuantity": {
            "value": round(probability * 100, 2),
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "code": "%",
        },
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "POS" if threshold_met else "NEG",
                        "display": "Positive" if threshold_met else "Negative",
                    }
                ]
            }
        ],
    }


@router.post("/export/hl7", response_model=HL7ExportResponse)
@limiter.limit("20/minute")
async def export_hl7(request: Request, body: HL7ExportRequest):
    resource_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    threshold = 0.15

    # Determine final class after radiologist review
    final_class = body.top_class
    if body.radiologist_verdict == "reject":
        final_class = "none"
    elif body.radiologist_verdict == "correct" and body.corrected_class:
        final_class = body.corrected_class

    detected = final_class not in ("none", "no_hemorrhage") and body.confidence >= threshold

    # Conclusion text
    snomed_finding = HEMORRHAGE_SNOMED.get(final_class, HEMORRHAGE_SNOMED["any"]) if detected else None
    conclusion_text = (
        f"AI-assisted CT analysis detected {final_class.replace('_', ' ')} "
        f"with {round(body.confidence * 100, 1)}% confidence (Q-Sentinel Mesh, {body.model_type})."
        if detected
        else "No intracranial hemorrhage detected by AI-assisted CT analysis (Q-Sentinel Mesh)."
    )
    if body.radiologist_verdict:
        verdict_label = {"confirm": "Confirmed", "reject": "Rejected", "correct": "Corrected"}.get(
            body.radiologist_verdict, body.radiologist_verdict
        )
        conclusion_text += f" Radiologist review: {verdict_label}."

    # Build contained Observations for each subtype
    observations = []
    for htype, prob in body.probabilities.items():
        if htype == "any":
            continue
        snomed = HEMORRHAGE_SNOMED.get(htype)
        if snomed:
            obs = _build_observation(snomed["code"], snomed["display"], prob, prob >= threshold)
            observations.append(obs)

    fhir = {
        "resourceType": "DiagnosticReport",
        "id": resource_id,
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/DiagnosticReport"],
            "source": "Q-Sentinel-Mesh/1.0",
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "RAD",
                        "display": "Radiology",
                    }
                ]
            }
        ],
        "code": {"coding": [LOINC_CT_HEAD], "text": "CT Head — Hemorrhage Detection"},
        "subject": {"display": body.filename or "Unknown patient"},
        "effectiveDateTime": now,
        "issued": now,
        "performer": [
            {"display": f"Q-Sentinel Mesh AI ({body.model_type})"},
            {"display": body.hospital},
        ],
        "result": [{"reference": f"#{obs['id']}", "display": obs["code"]["text"]} for obs in observations],
        "contained": observations,
        "conclusion": conclusion_text,
        "conclusionCode": (
            [{"coding": [{"system": "http://snomed.info/sct", **snomed_finding}]}]
            if snomed_finding
            else [{"coding": [{"system": "http://snomed.info/sct", **SNOMED_NO_FINDING}]}]
        ),
        "extension": [
            {
                "url": "https://qsentinel.ai/fhir/StructureDefinition/ai-confidence",
                "valueDecimal": round(body.confidence, 4),
            },
            {
                "url": "https://qsentinel.ai/fhir/StructureDefinition/ai-model",
                "valueString": body.model_type or "hybrid",
            },
            {
                "url": "https://qsentinel.ai/fhir/StructureDefinition/radiologist-verdict",
                "valueString": body.radiologist_verdict or "pending",
            },
            {
                "url": "https://qsentinel.ai/fhir/StructureDefinition/pqc-encrypted",
                "valueBoolean": True,
            },
        ],
    }

    return HL7ExportResponse(fhir_json=fhir, resource_id=resource_id)
