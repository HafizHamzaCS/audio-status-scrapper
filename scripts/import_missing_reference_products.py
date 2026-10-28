"""Import and reconcile the 45 missing SoundImports reference products.

Can be run standalone or invoked from the API/CLI.
Safe and idempotent.
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session_factory
from app import crud
from app.timeutils import utc_now
from scraper.soundimports import SoundImportsScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_missing")

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


async def import_missing_products(items: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    items_to_import = items or MISSING_PRODUCTS_DATA
    logger.info("Starting import of %d missing products...", len(items_to_import))
    scraper = SoundImportsScraper()

    # Pre-sync categories if present in items
    succeeded = 0
    failed = 0
    results = []

    try:
        # First ensure categories from sitemap are in DB so relationships link
        categories = await scraper.discover_categories()
        async with async_session_factory() as db:
            for cat in categories:
                await crud.upsert_category_with_parent(
                    db,
                    name=cat["name"],
                    slug=cat["slug"],
                    canonical_path=cat["canonical_path"],
                    url=cat["url"],
                    level=cat.get("level", 0),
                    parent_path_ref=cat.get("parent_path"),
                    source_count=cat.get("source_count", 0),
                )
            await db.commit()

        # Also ensure peerless-by-tymphany-woofers category exists
        async with async_session_factory() as db:
            await crud.upsert_category_with_parent(
                db,
                name="Peerless by Tymphany woofers",
                slug="peerless-by-tymphany-woofers",
                canonical_path="/en/peerless-by-tymphany-woofers/",
                url="https://www.soundimports.eu/en/peerless-by-tymphany-woofers/",
                level=1,
            )
            await db.commit()

        for idx, item in enumerate(items_to_import, 1):
            ref_url = item["reference_url"]
            expected_sku = item["sku"]
            ref_id = item["reference_id"]

            try:
                logger.info("[%d/%d] Fetching %s (%s)...", idx, len(items_to_import), expected_sku, ref_url)
                detail_json = await scraper.get_product_detail(ref_url)
                html_doc = None
                try:
                    html_doc = await scraper._client.fetch_html(ref_url)
                except Exception:
                    pass

                prod_data = scraper.extract_product_detail(detail_json, html_doc=html_doc)

                # Collect all canonical category paths from product JSON
                cat_paths = []
                for c in prod_data.get("product_categories", []):
                    if c.get("canonical_path"):
                        cat_paths.append(c["canonical_path"])

                async with async_session_factory() as db:
                    db_prod, is_new, (rel_c, rel_e) = await crud.upsert_product(
                        db,
                        product_id=prod_data["product_id"] or ref_id,
                        sku=prod_data["sku"] or expected_sku,
                        ean=prod_data.get("ean"),
                        title=prod_data.get("title") or item["title"],
                        description=prod_data.get("description"),
                        short_description=prod_data.get("short_description"),
                        long_description=prod_data.get("long_description"),
                        regular_price=prod_data.get("regular_price"),
                        price=prod_data.get("price"),
                        stock=prod_data.get("stock"),
                        stock_status=prod_data.get("stock_status"),
                        brand=prod_data.get("brand"),
                        currency=prod_data.get("currency", "EUR"),
                        url=prod_data.get("url") or ref_url,
                        category_ids=prod_data.get("category_ids") or "",
                        raw_json=prod_data.get("raw_json"),
                        images=prod_data.get("images", []),
                        attributes=prod_data.get("attributes", []),
                        product_categories_paths=cat_paths,
                    )
                succeeded += 1
                results.append({
                    "sku": db_prod.sku,
                    "db_id": db_prod.id,
                    "product_id": db_prod.product_id,
                    "title": db_prod.title,
                    "price": db_prod.price,
                    "stock": db_prod.stock,
                    "status": "imported" if is_new else "updated",
                    "categories_count": len(cat_paths),
                })
            except Exception as exc:
                failed += 1
                logger.error("Failed to import %s (%s): %s", expected_sku, ref_url, exc)
                results.append({"sku": expected_sku, "error": str(exc), "status": "failed"})

        # Also repair NE85W-04 (Peerless by Tymphany NE85W-04 Full-range Woofer)
        try:
            logger.info("Ensuring NE85W-04 category assignment...")
            ne_url = "https://www.soundimports.eu/en/peerless-by-tymphany-ne85w-04.html"
            ne_json = await scraper.get_product_detail(ne_url)
            ne_html = None
            try:
                ne_html = await scraper._client.fetch_html(ne_url)
            except Exception:
                pass
            ne_data = scraper.extract_product_detail(ne_json, html_doc=ne_html)
            ne_cats = [c["canonical_path"] for c in ne_data.get("product_categories", []) if c.get("canonical_path")]
            if "/en/peerless-by-tymphany-woofers/" not in ne_cats:
                ne_cats.append("/en/peerless-by-tymphany-woofers/")

            async with async_session_factory() as db:
                await crud.upsert_product(
                    db,
                    product_id=ne_data["product_id"] or "65895191",
                    sku=ne_data["sku"] or "NE85W-04",
                    ean=ne_data.get("ean"),
                    title=ne_data.get("title"),
                    description=ne_data.get("description"),
                    short_description=ne_data.get("short_description"),
                    long_description=ne_data.get("long_description"),
                    regular_price=ne_data.get("regular_price"),
                    price=ne_data.get("price"),
                    stock=ne_data.get("stock"),
                    stock_status=ne_data.get("stock_status"),
                    brand=ne_data.get("brand"),
                    currency=ne_data.get("currency", "EUR"),
                    url=ne_data.get("url") or ne_url,
                    category_ids=ne_data.get("category_ids") or "",
                    raw_json=ne_data.get("raw_json"),
                    images=ne_data.get("images", []),
                    attributes=ne_data.get("attributes", []),
                    product_categories_paths=ne_cats,
                )
            logger.info("NE85W-04 repaired and linked to categories: %s", ne_cats)
        except Exception as exc:
            logger.warning("Could not re-link NE85W-04: %s", exc)

    finally:
        await scraper._client.close()

    summary = {
        "total_targets": len(items_to_import),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
    logger.info("Finished: %d succeeded, %d failed", succeeded, failed)
    return summary


if __name__ == "__main__":
    asyncio.run(import_missing_products())
