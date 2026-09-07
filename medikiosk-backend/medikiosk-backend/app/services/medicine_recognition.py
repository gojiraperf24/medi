"""
Medicine packaging recognition.

The OCR/compound-detection step (would use OpenCV + a trained model or
Tesseract in production) is MOCKED — there's no real model wired up. The
Jan Aushadhi generic-alternative LOOKUP is real: a small but genuine
reference table of common brand -> generic compound -> PMBJP (Jan Aushadhi)
price mappings, keyed by compound so it works regardless of which OCR
result comes back from the mocked recognition step.

Swap `recognize_medicine_image` for a real OpenCV/PyTorch pipeline (e.g.
a fine-tuned OCR + a brand-name classifier) without touching the lookup
table or the API route.
"""
import random

# A small real reference set of common Jan Aushadhi (PMBJP) generic
# equivalents. Prices are illustrative PMBJP price-list figures and should
# be refreshed from https://janaushadhi.gov.in for production use.
JAN_AUSHADHI_TABLE: dict[str, list[dict]] = {
    "paracetamol": [
        {"generic_name": "Paracetamol 500mg (PMBJP)", "compound": "Paracetamol", "estimated_price_inr": 8.0, "pack_size": "10 tablets"},
    ],
    "azithromycin": [
        {"generic_name": "Azithromycin 500mg (PMBJP)", "compound": "Azithromycin", "estimated_price_inr": 25.0, "pack_size": "3 tablets"},
    ],
    "metformin": [
        {"generic_name": "Metformin 500mg (PMBJP)", "compound": "Metformin Hydrochloride", "estimated_price_inr": 12.0, "pack_size": "10 tablets"},
    ],
    "amlodipine": [
        {"generic_name": "Amlodipine 5mg (PMBJP)", "compound": "Amlodipine Besylate", "estimated_price_inr": 9.0, "pack_size": "10 tablets"},
    ],
    "omeprazole": [
        {"generic_name": "Omeprazole 20mg (PMBJP)", "compound": "Omeprazole", "estimated_price_inr": 10.0, "pack_size": "10 capsules"},
    ],
    "cetirizine": [
        {"generic_name": "Cetirizine 10mg (PMBJP)", "compound": "Cetirizine Hydrochloride", "estimated_price_inr": 5.0, "pack_size": "10 tablets"},
    ],
    "amoxicillin": [
        {"generic_name": "Amoxicillin 500mg (PMBJP)", "compound": "Amoxicillin", "estimated_price_inr": 18.0, "pack_size": "10 capsules"},
    ],
}

# Common brand names mapped to the compound key above — this is the piece a
# real OCR+classifier model would replace/expand enormously.
_MOCK_BRAND_TO_COMPOUND = {
    "crocin": "paracetamol",
    "dolo": "paracetamol",
    "calpol": "paracetamol",
    "azithral": "azithromycin",
    "azee": "azithromycin",
    "glycomet": "metformin",
    "amlong": "amlodipine",
    "omez": "omeprazole",
    "cetzine": "cetirizine",
    "mox": "amoxicillin",
}


def recognize_medicine_image(image_ref: str | None) -> dict:
    """
    MOCKED recognition step. Returns a plausible brand/compound/OCR-text
    result. `image_ref` is accepted (and stored on the record) so the real
    pipeline can be dropped in later without changing the route or schema —
    it currently just picks a random known brand to keep the demo varied.
    """
    brand = random.choice(list(_MOCK_BRAND_TO_COMPOUND.keys()))
    compound_key = _MOCK_BRAND_TO_COMPOUND[brand]
    compound_display = JAN_AUSHADHI_TABLE[compound_key][0]["compound"]
    return {
        "detected_brand_name": brand.capitalize(),
        "detected_compound": compound_display,
        "ocr_raw_text": f"{brand.upper()} 500 TAB\nMFG: 2025\nEXP: 2027",
        "confidence": round(random.uniform(0.78, 0.97), 2),
        "_compound_key": compound_key,
    }


def find_jan_aushadhi_alternatives(compound_key_or_name: str) -> list[dict]:
    key = compound_key_or_name.strip().lower()
    if key in JAN_AUSHADHI_TABLE:
        return JAN_AUSHADHI_TABLE[key]
    # Fall back to substring match against compound display names.
    for k, entries in JAN_AUSHADHI_TABLE.items():
        if key in entries[0]["compound"].lower():
            return entries
    return []
