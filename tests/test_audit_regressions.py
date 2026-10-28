import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models import Product, Category, product_categories
from app import crud
from app.timeutils import utc_now


@pytest.mark.asyncio
async def test_validate_gtin_checksum():
    # Valid standard barcodes
    valid_8 = "96385074"
    valid_12 = "012345678905"
    valid_13 = "8719324021234"
    valid_14 = "10012345678902"

    assert crud.validate_gtin(valid_8)[0] is True
    assert crud.validate_gtin(valid_12)[0] is True
    assert crud.validate_gtin(valid_13)[0] is True
    assert crud.validate_gtin(valid_14)[0] is True
    assert crud.validate_gtin(None)[0] is True
    assert crud.validate_gtin("")[0] is True

    # Invalid barcodes
    assert crud.validate_gtin("8719324021235")[0] is False  # wrong check digit
    assert crud.validate_gtin("12345")[0] is False  # wrong length
    assert crud.validate_gtin("ABC1234567890")[0] is False  # non-digit


@pytest.mark.asyncio
async def test_compute_content_hash_stability():
    h1 = crud.compute_content_hash(
        title="Speaker Kit",
        short_description="Short desc",
        description="Long desc",
        long_description="Details",
        price=99.95,
        regular_price=99.95,
        brand="Dayton Audio",
        ean="8719324021234",
        currency="EUR",
        attributes=[{"attribute_name": "Power", "attribute_value": "100W", "sort_order": 0}],
        images=[{"image_url": "https://example.com/img1.jpg", "sort_order": 0}],
    )
    # Same content produces identical hash
    h2 = crud.compute_content_hash(
        title="Speaker Kit",
        short_description="Short desc",
        description="Long desc",
        long_description="Details",
        price=99.95,
        regular_price=99.95,
        brand="Dayton Audio",
        ean="8719324021234",
        currency="EUR",
        attributes=[{"attribute_name": "Power", "attribute_value": "100W", "sort_order": 0}],
        images=[{"image_url": "https://example.com/img1.jpg", "sort_order": 0}],
    )
    assert h1 == h2

    # Modified price changes hash
    h3 = crud.compute_content_hash(
        title="Speaker Kit",
        short_description="Short desc",
        description="Long desc",
        long_description="Details",
        price=109.95,
        regular_price=99.95,
        brand="Dayton Audio",
        ean="8719324021234",
        currency="EUR",
        attributes=[{"attribute_name": "Power", "attribute_value": "100W", "sort_order": 0}],
        images=[{"image_url": "https://example.com/img1.jpg", "sort_order": 0}],
    )
    assert h1 != h3


@pytest.mark.asyncio
async def test_upsert_product_identity_and_timestamps(session_factory):
    async with session_factory() as db:
        # 1. Insert new product
        p1, is_new, _ = await crud.upsert_product(
            db,
            product_id="164891798",
            sku="Service Part 63",
            ean=None,
            title="DIY Speaker Assembly Kit Small",
            description="Kit description",
            long_description="Long kit details",
            price=73.95,
            stock=0,
            stock_status="on_backorder",
            brand="SoundImports",
            currency="EUR",
            url="https://www.soundimports.eu/en/service-part-63.html",
            category_ids="accessories",
            raw_json=None,
            images=[],
            attributes=[],
        )
        assert is_new is True
        assert p1.product_id == "164891798"
        assert p1.sku == "Service Part 63"
        assert p1.stock == 0
        assert p1.stock_status == "on_backorder"
        orig_content_updated = p1.content_updated_at

        # 2. Re-upsert with same content - content_updated_at MUST NOT change
        p2, is_new2, _ = await crud.upsert_product(
            db,
            product_id="164891798",
            sku="Service Part 63",
            ean=None,
            title="DIY Speaker Assembly Kit Small",
            description="Kit description",
            long_description="Long kit details",
            price=73.95,
            stock=0,
            stock_status="on_backorder",
            brand="SoundImports",
            currency="EUR",
            url="https://www.soundimports.eu/en/service-part-63.html",
            category_ids="accessories",
            raw_json=None,
            images=[],
            attributes=[],
        )
        assert is_new2 is False
        assert p2.id == p1.id
        assert p2.content_updated_at == orig_content_updated

        # 3. Change stock only - stock_updated_at updates, content_updated_at unchanged
        p3, is_new3, _ = await crud.upsert_product(
            db,
            product_id="164891798",
            sku="Service Part 63",
            ean=None,
            title="DIY Speaker Assembly Kit Small",
            description="Kit description",
            long_description="Long kit details",
            price=73.95,
            stock=15,
            stock_status="in_stock",
            brand="SoundImports",
            currency="EUR",
            url="https://www.soundimports.eu/en/service-part-63.html",
            category_ids="accessories",
            raw_json=None,
            images=[],
            attributes=[],
        )
        assert is_new3 is False
        assert p3.stock == 15
        assert p3.stock_status == "in_stock"
        assert p3.content_updated_at == orig_content_updated
        assert p3.stock_updated_at is not None


@pytest.mark.asyncio
async def test_get_product_by_sku_encoded_and_fallback(session_factory):
    async with session_factory() as db:
        await crud.upsert_product(
            db,
            product_id="143247625",
            sku="R-33/Supreme",
            ean=None,
            title="Morel Repair set",
            description=None,
            long_description=None,
            price=150.0,
            stock=5,
            stock_status="in_stock",
            brand="Morel",
            currency="EUR",
            url="https://www.soundimports.eu/en/morel-r-33supreme.html",
            category_ids="",
            raw_json=None,
            images=[],
            attributes=[],
        )

        # Retrieval by exact SKU
        prod1 = await crud.get_product_by_sku(db, "R-33/Supreme")
        assert prod1 is not None
        assert prod1.product_id == "143247625"

        # Retrieval by URL-encoded SKU
        prod2 = await crud.get_product_by_sku(db, "R-33%2FSupreme")
        assert prod2 is not None
        assert prod2.id == prod1.id

        # Retrieval by case-insensitive SKU
        prod3 = await crud.get_product_by_sku(db, "r-33/supreme")
        assert prod3 is not None
        assert prod3.id == prod1.id


@pytest.mark.asyncio
async def test_safe_deactivation_protects_local_products(session_factory):
    async with session_factory() as db:
        # SoundImports product (has product_id)
        p_si, _, _ = await crud.upsert_product(
            db,
            product_id="999999",
            sku="SI-ITEM-1",
            ean=None,
            title="SoundImports Item",
            description=None,
            long_description=None,
            price=10.0,
            stock=1,
            stock_status="in_stock",
            brand="SI",
            currency="EUR",
            url="https://example.com/si",
            category_ids="",
            raw_json=None,
            images=[],
            attributes=[],
        )
        # AudioStatus / Car Audio product (product_id is None)
        p_local = Product(
            product_id=None,
            sku="CAR-AUDIO-1",
            title="Local Car Audio Subwoofer",
            price=299.0,
            is_active=True,
            missing_streak=0,
        )
        db.add(p_local)
        await db.commit()

        # Run mark_unseen_products_missing with a set that does NOT contain "999999"
        deactivated = await crud.mark_unseen_products_missing(
            db, seen_product_ids={"other_id"}, confirmation_threshold=2
        )
        assert deactivated == 0  # streak is 1, not yet deactivated

        await db.refresh(p_si)
        await db.refresh(p_local)
        assert p_si.missing_streak == 1
        assert p_si.is_active is True
        assert p_local.missing_streak == 0
        assert p_local.is_active is True

        # Second missed scan: passes threshold=2
        deactivated2 = await crud.mark_unseen_products_missing(
            db, seen_product_ids={"other_id"}, confirmation_threshold=2
        )
        assert deactivated2 == 1

        await db.refresh(p_si)
        await db.refresh(p_local)
        assert p_si.missing_streak == 2
        assert p_si.is_active is False  # Deactivated safely
        assert p_local.missing_streak == 0
        assert p_local.is_active is True  # Local product untouched!


@pytest.mark.asyncio
async def test_cursor_pagination_stability(session_factory):
    async with session_factory() as db:
        # Create 10 products
        for i in range(1, 11):
            await crud.upsert_product(
                db,
                product_id=f"TEST-{i}",
                sku=f"SKU-TEST-{i:02d}",
                ean=None,
                title=f"Test Product {i}",
                description=None,
                long_description=None,
                price=float(i * 10),
                stock=i,
                stock_status="in_stock",
                brand="TestBrand",
                currency="EUR",
                url=None,
                category_ids="",
                raw_json=None,
                images=[],
                attributes=[],
            )

        # Fetch page 1 (5 items)
        page1, total = await crud.get_products_paginated(db, per_page=5, after_id=None)
        assert len(page1) == 5
        assert total == 10
        assert page1[0].sku == "SKU-TEST-01"

        # Fetch page 2 using cursor (after_id = page1[-1].id)
        cursor_id = page1[-1].id
        page2, _ = await crud.get_products_paginated(db, per_page=5, after_id=cursor_id)
        assert len(page2) == 5
        assert page2[0].sku == "SKU-TEST-06"
        assert page2[-1].sku == "SKU-TEST-10"

        # Ensure no overlap between cursor pages
        p1_ids = {p.id for p in page1}
        p2_ids = {p.id for p in page2}
        assert p1_ids.isdisjoint(p2_ids)
