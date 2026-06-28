"""Phone models API — returns real-world phone specs per brand."""

from fastapi import APIRouter, HTTPException

from src.utils.config import load_yaml

router = APIRouter()


def _load_phones_data() -> dict:
    """Load phones YAML, with caching via lru_cache on load_yaml."""
    raw = load_yaml("phones.yaml")
    return raw.get("brands", {})


@router.get("/phones/{brand_id}")
async def get_brand_phones(brand_id: str):
    """Get real phone models for a specific brand.

    Returns brand info plus list of models with key specs.
    """
    brands = _load_phones_data()
    brand = brands.get(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand not found: {brand_id}")
    return brand


@router.get("/phones")
async def list_all_phones():
    """List all brands and their phone model counts.

    Useful for brand selection UI and quick browsing.
    """
    brands = _load_phones_data()
    return {
        brand_id: {
            "name": data["name"],
            "model_count": len(data.get("models", [])),
            "models": [
                {
                    "id": m["id"],
                    "model": m["model"],
                    "release_year": m.get("release_year"),
                    "tier": m.get("tier"),
                    "price_range": m.get("price_range"),
                }
                for m in data.get("models", [])
            ],
        }
        for brand_id, data in brands.items()
    }
