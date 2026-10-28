import httpx
import json
import urllib.parse

BASE_URL = "https://audio-status-scrapper-production.up.railway.app"

SKUS = [
    "Service Part 63", "Service Part 64", "Service Part 65", "Service Part 66", "Service Part 67",
    "R-33/Supreme", "XBS25-4-bundle", "XBS100-4-bundle", "XBS200-4-bundle", "Service Part 29",
    "Service Part 28", "Service Part 27", "Service Part 26", "Service Part 25", "Service Part 24",
    "Service Part 23", "Service Part 22", "Service Part 21", "JDM-WPIO-0.01", "JDM-WPIO-0.022",
    "JDM-WPIO-0.033", "JDM-WPIO-0.047", "JDM-WPIO-0.068", "JDM-WPIO-0.082", "JDM-WPIO-0.1",
    "JDM-WPIO-0.22", "JDM-WPIO-0.33", "JDM-WPIO-0.47", "JDM-PIO-12-CU-0.22", "JDM-PIO-12-CU-0.27",
    "JDM-PIO-12-CU-0.33", "JDM-PIO-12-CU-0.82", "JDM-PIO-12-CU-1", "JDM-PIO-12-CU-1.2",
    "JDM-PIO-12-CU-1.5", "CAP-5180", "VBASE-166", "VBASE-171", "CT-conn1", "KABT-SFC",
    "207530", "HQ58/3.9/150", "000-8555", "MZF-4025", "AA-JA11117"
]

def test_live():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health
        try:
            r = client.get("/health")
            print(f"GET /health: {r.status_code} -> {r.json()}")
        except Exception as e:
            print(f"GET /health error: {e}")

        # 2. Stats
        try:
            r = client.get("/api/stats")
            print(f"GET /api/stats: {r.status_code} -> {r.json()}")
        except Exception as e:
            print(f"GET /api/stats error: {e}")

        # 3. Delta
        try:
            r = client.get("/api/products/delta?limit=2")
            print(f"GET /api/products/delta: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print("Delta keys:", list(data.keys()))
                print(f"has_more: {data.get('has_more')}, next_cursor: {data.get('next_cursor')}")
        except Exception as e:
            print(f"GET /api/products/delta error: {e}")

        # 4. Check 45 SKUs
        print("\n--- Checking 45 SKUs ---")
        passed = 0
        failed = []
        for sku in SKUS:
            enc_sku = urllib.parse.quote(sku, safe='')
            url = f"/api/product/sku/{enc_sku}"
            try:
                r = client.get(url)
                if r.status_code == 200:
                    passed += 1
                    data = r.json()
                    print(f"[200 OK] {sku} -> id={data.get('id')}, product_id={data.get('product_id')}, sku={data.get('sku')}")
                else:
                    failed.append((sku, r.status_code, url))
                    print(f"[{r.status_code}] {sku} ({url})")
            except Exception as e:
                failed.append((sku, str(e), url))
                print(f"[ERR] {sku}: {e}")

        print(f"\nSummary: {passed}/{len(SKUS)} passed.")
        if failed:
            print(f"Failed ({len(failed)}):")
            for item in failed:
                print(f"  {item[0]}: status={item[1]}, url={item[2]}")

if __name__ == "__main__":
    test_live()
