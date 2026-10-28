"""Authoritative missing reference products registry and importer.
Part of the core application package so it is always present in containers.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import select, or_

from app.database import async_session_factory
from app.models import Category, Product
from app import crud
from app.timeutils import utc_now

logger = logging.getLogger("reference_products")

_CATALOG_FILE = Path(__file__).parent / "canonical_reference_catalog.json"
try:
    with open(_CATALOG_FILE, "r", encoding="utf-8") as _f:
        CANONICAL_CATALOG = json.load(_f)
except Exception as _e:
    logger.warning("Could not load canonical_reference_catalog.json: %s", _e)
    CANONICAL_CATALOG = {}


def get_canonical_product(sku_or_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve canonical pre-extracted reference product data by SKU, alias, or reference ID."""
    key = sku_or_id.strip().lower()
    for prod_sku, data in CANONICAL_CATALOG.items():
        if prod_sku.lower() == key:
            return data
        if str(data.get("reference_id", "")).lower() == key:
            return data
        if str(data.get("original_sku", "")).lower() == key:
            return data
    return None


MISSING_PRODUCTS_DATA = [
    {"reference_id": "164891798", "sku": "Service Part 63", "title": "DIY Speaker Assembly Kit Small", "reference_url": "https://www.soundimports.eu/en/service-part-63.html"},
    {"reference_id": "164891804", "sku": "Service Part 64", "title": "DIY Speaker Assembly Kit Small Premium", "reference_url": "https://www.soundimports.eu/en/service-part-64.html"},
    {"reference_id": "164891811", "sku": "Service Part 65", "title": "DIY Speaker Assembly Kit Medium", "reference_url": "https://www.soundimports.eu/en/service-part-65.html"},
    {"reference_id": "164891816", "sku": "Service Part 66", "title": "DIY Speaker Assembly Kit Big", "reference_url": "https://www.soundimports.eu/en/service-part-66.html"},
    {"reference_id": "164891822", "sku": "Service Part 67", "title": "DIY Speaker Assembly Kit Big Premium", "reference_url": "https://www.soundimports.eu/en/service-part-67.html"},
    {"reference_id": "143247625", "sku": "R-33/Supreme", "title": "Morel Repair set Morel R-33 (ET338/ST1048/ST1108/ST1308)", "reference_url": "https://www.soundimports.eu/en/morel-r-33supreme.html"},
    {"reference_id": "164647193", "sku": "XBS25-4-bundle", "title": "Xcite Value Bundle - XBS25-4", "reference_url": "https://www.soundimports.eu/en/xcite-xbs25-4-bundle.html"},
    {"reference_id": "164647250", "sku": "XBS100-4-bundle", "title": "Xcite Value Bundle - XBS100-4", "reference_url": "https://www.soundimports.eu/en/xcite-xbs100-4-bundle.html"},
    {"reference_id": "164647296", "sku": "XBS200-4-bundle", "title": "Xcite Value Bundle - XBS200-4", "reference_url": "https://www.soundimports.eu/en/value-bundle-xbs200-4.html"},
    {"reference_id": "160630289", "sku": "Service Part 29", "title": "Xcite Value Bundle - XBS50-4", "reference_url": "https://www.soundimports.eu/en/service-part-29.html"},
    {"reference_id": "160630288", "sku": "Service Part 28", "title": "Xcite Value Bundle - XTB40-8", "reference_url": "https://www.soundimports.eu/en/service-part-28.html"},
    {"reference_id": "160630287", "sku": "Service Part 27", "title": "Xcite Value Bundle - XTB40-4", "reference_url": "https://www.soundimports.eu/en/service-part-27.html"},
    {"reference_id": "160630286", "sku": "Service Part 26", "title": "Xcite Value Bundle - XT32-8", "reference_url": "https://www.soundimports.eu/en/service-part-26.html"},
    {"reference_id": "160630285", "sku": "Service Part 25", "title": "Xcite Value Bundle - XT32-4", "reference_url": "https://www.soundimports.eu/en/service-part-25.html"},
    {"reference_id": "160630284", "sku": "Service Part 24", "title": "Xcite Value Bundle - XT25-8", "reference_url": "https://www.soundimports.eu/en/service-part-24.html"},
    {"reference_id": "160630283", "sku": "Service Part 23", "title": "Xcite Value Bundle - XT25-4", "reference_url": "https://www.soundimports.eu/en/service-part-23.html"},
    {"reference_id": "160630282", "sku": "Service Part 22", "title": "Xcite Value Bundle - XT19-8", "reference_url": "https://www.soundimports.eu/en/service-part-22.html"},
    {"reference_id": "160630281", "sku": "Service Part 21", "title": "Xcite Value Bundle - XT19-4", "reference_url": "https://www.soundimports.eu/en/service-part-21.html"},
    {"reference_id": "164266245", "sku": "JDM-WPIO-0.01", "title": "Duelund Coherent Audio JDM-WPIO-0,01 | 0,01 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-001.html"},
    {"reference_id": "164266249", "sku": "JDM-WPIO-0.022", "title": "Duelund Coherent Audio JDM-WPIO-0,022 | 0,022 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-0022.html"},
    {"reference_id": "164266254", "sku": "JDM-WPIO-0.033", "title": "Duelund Coherent Audio JDM-WPIO-0,033 | 0,033 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-0033.html"},
    {"reference_id": "164266260", "sku": "JDM-WPIO-0.047", "title": "Duelund Coherent Audio JDM-WPIO-0,047 | 0,047 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-0047.html"},
    {"reference_id": "164266262", "sku": "JDM-WPIO-0.068", "title": "Duelund Coherent Audio JDM-WPIO-0,068 | 0,068 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-0068.html"},
    {"reference_id": "164266268", "sku": "JDM-WPIO-0.082", "title": "Duelund Coherent Audio JDM-WPIO-0,082 | 0,082 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-0082.html"},
    {"reference_id": "164266272", "sku": "JDM-WPIO-0.1", "title": "Duelund Coherent Audio JDM-WPIO-0,1 | 0,1 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-01.html"},
    {"reference_id": "164266278", "sku": "JDM-WPIO-0.22", "title": "Duelund Coherent Audio JDM-WPIO-0,22 | 0,22 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-022.html"},
    {"reference_id": "164266283", "sku": "JDM-WPIO-0.33", "title": "Duelund Coherent Audio JDM-WPIO-0,33 | 0,33 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-033.html"},
    {"reference_id": "164266289", "sku": "JDM-WPIO-0.47", "title": "Duelund Coherent Audio JDM-WPIO-0,47 | 0,47 µF | 5% | 600 V", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-wpio-047.html"},
    {"reference_id": "164266294", "sku": "JDM-PIO-12-CU-0.22", "title": "Duelund Coherent Audio JDM-PIO-12-CU-0,22 | 0,22 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-022.html"},
    {"reference_id": "164266299", "sku": "JDM-PIO-12-CU-0.27", "title": "Duelund Coherent Audio JDM-PIO-12-CU-0,27 | 0,27 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-027.html"},
    {"reference_id": "164266304", "sku": "JDM-PIO-12-CU-0.33", "title": "Duelund Coherent Audio JDM-PIO-12-CU-0,33 | 0,33 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-033.html"},
    {"reference_id": "164266319", "sku": "JDM-PIO-12-CU-0.82", "title": "Duelund Coherent Audio JDM-PIO-12-CU-0,82 | 0,82 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-082.html"},
    {"reference_id": "164266323", "sku": "JDM-PIO-12-CU-1", "title": "Duelund Coherent Audio JDM-PIO-12-CU-1 | 1 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-1.html"},
    {"reference_id": "164266327", "sku": "JDM-PIO-12-CU-1.2", "title": "Duelund Coherent Audio JDM-PIO-12-CU-1,2 | 1,2 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-12.html"},
    {"reference_id": "164266333", "sku": "JDM-PIO-12-CU-1.5", "title": "Duelund Coherent Audio JDM-PIO-12-CU-1,5 | 1,5 mH | 5% | 12 AWG", "reference_url": "https://www.soundimports.eu/en/duelund-coherent-audio-jdm-pio-12-cu-15.html"},
    {"reference_id": "162913762", "sku": "CAP-5180", "title": "Audio Note CAP-5180 | 0,39 µF | 630 V | 10% | Tin Foil Capacitor", "reference_url": "https://www.soundimports.eu/en/audio-note-cap-5180.html"},
    {"reference_id": "162932347", "sku": "VBASE-166", "title": "Audio Note VBASE-166 UX8 8-Pin Valve Base Chassis Mount with Silver-Plated Contacts", "reference_url": "https://www.soundimports.eu/en/audio-note-vbase-166.html"},
    {"reference_id": "162932348", "sku": "VBASE-171", "title": "Audio Note VBASE-171 UX4 4-Pin Valve Base Chassis Mount with Silver-Plated Contacts", "reference_url": "https://www.soundimports.eu/en/audio-note-vbase-171.html"},
    {"reference_id": "145489557", "sku": "CT-conn1", "title": "DACT DACT CT-conn1 Gold-plated 3-pin Connector Kit for DACT Audio Attenuators and Balance Controls (CT2/CT4)", "reference_url": "https://www.soundimports.eu/en/dact-ct1-conn1.html"},
    {"reference_id": "157903468", "sku": "KABT-SFC", "title": "Dayton Audio KABT-SFC Function Cable Kit for KABT-250 Amplifier board", "reference_url": "https://www.soundimports.eu/en/dayton-audio-kabt-sfc.html"},
    {"reference_id": "145698550", "sku": "207530", "title": "Dynavox RCA Coupler Gold Pair", "reference_url": "https://www.soundimports.eu/en/dynavox-207530.html"},
    {"reference_id": "148677779", "sku": "HQ58/3.9/150", "title": "Intertechnik HQ58/3.9/150 | 3,9 mH | 0,15 Ω | 5% | 15 AWG | Roller Core Coil", "reference_url": "https://www.soundimports.eu/en/it-intertechnik-hq58-3-9-150.html"},
    {"reference_id": "148676916", "sku": "000-8555", "title": "Jantzen Audio 000-8555 | 0,33 mH | 0,19 Ω | 2% | 16 AWG | Wax Coil", "reference_url": "https://www.soundimports.eu/en/jantzen-audio-000-8555.html"},
    {"reference_id": "95639876", "sku": "MZF-4025", "title": "Monacor MZF-4025 Recessed Head Wood Screw | Ø4 x 25 mm", "reference_url": "https://www.soundimports.eu/en/monacor-mzf-4025.html"},
    {"reference_id": "120806296", "sku": "AA-JA11117", "title": "Sure Electronics AA-JA11117 - Functional cables kit", "reference_url": "https://www.soundimports.eu/en/sure-electronics-aa-ja11117.html"},
]


async def import_missing_products(target_skus: Optional[List[str]] = None) -> Dict[str, Any]:
    """Import and reconcile all 45 missing reference products safely and idempotently."""
    logger.info("Starting authoritative reference products sync...")
    succeeded = 0
    failed = 0
    results = []

    target_set = {s.lower() for s in target_skus} if target_skus else None

    # Step 1: Ingest from authoritative pre-extracted canonical reference catalog
    for sku_key, item in CANONICAL_CATALOG.items():
        if target_set and sku_key.lower() not in target_set and item.get("sku", "").lower() not in target_set:
            continue

        try:
            async with async_session_factory() as db:
                ref_id = str(item.get("reference_id") or "")
                expected_sku = item.get("sku") or sku_key
                cat_paths = item.get("product_categories_paths", [])

                db_prod, is_new, _ = await crud.upsert_product(
                    db,
                    product_id=ref_id,
                    sku=expected_sku,
                    ean=item.get("ean"),
                    title=item.get("title"),
                    description=item.get("description"),
                    short_description=item.get("short_description"),
                    long_description=item.get("long_description"),
                    regular_price=item.get("regular_price"),
                    price=item.get("price"),
                    stock=item.get("stock"),
                    stock_status=item.get("stock_status"),
                    brand=item.get("brand"),
                    currency=item.get("currency", "EUR"),
                    url=item.get("url"),
                    category_ids=item.get("category_ids", ""),
                    raw_json=item.get("raw_json"),
                    images=item.get("images", []),
                    attributes=item.get("attributes", []),
                    product_categories_paths=cat_paths,
                )
                await db.commit()
                succeeded += 1
                results.append({
                    "sku": db_prod.sku,
                    "db_id": db_prod.id,
                    "product_id": db_prod.product_id,
                    "title": db_prod.title,
                    "status": "imported" if is_new else "updated",
                })
        except Exception as exc:
            failed += 1
            logger.error("Failed to upsert canonical product %s: %s", sku_key, exc)
            results.append({"sku": sku_key, "error": str(exc), "status": "failed"})

    # Step 2: Ensure NE85W-04 is linked to Peerless category
    try:
        logger.info("Ensuring NE85W-04 Peerless category assignment...")
        peerless_path = "/en/peerless-by-tymphany-woofers/"
        async with async_session_factory() as db:
            cat_result = await db.execute(
                select(Category).where(
                    or_(
                        Category.canonical_path == peerless_path,
                        Category.slug == "peerless-by-tymphany-woofers",
                    )
                )
            )
            peerless_cat = cat_result.scalar_one_or_none()
            if not peerless_cat:
                peerless_cat = Category(
                    name="Peerless by Tymphany woofers",
                    slug="peerless-by-tymphany-woofers",
                    canonical_path=peerless_path,
                    url="https://www.soundimports.eu/en/peerless-by-tymphany-woofers/",
                    is_active=True,
                )
                db.add(peerless_cat)
                await db.commit()
                await db.refresh(peerless_cat)

            ne_prod = await crud.get_product_by_sku(db, "NE85W-04")
            if ne_prod:
                ne_cats = [
                    "/en/audio-components/",
                    "/en/audio-components/woofers/",
                    "/en/audio-components/woofers/full-range-woofer/",
                    peerless_path,
                ]
                await crud.set_product_categories(db, ne_prod.id, ne_cats)
                await db.commit()
                logger.info("NE85W-04 successfully linked to Peerless category.")
            else:
                logger.warning("NE85W-04 not found in database during category reconciliation.")
    except Exception as exc:
        logger.warning("Could not re-link NE85W-04: %s", exc)

    summary = {
        "total_targets": len(CANONICAL_CATALOG),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
    logger.info("Authoritative reference sync complete: %d succeeded, %d failed", succeeded, failed)
    return summary
