"""Which E43 sources are reachable from this machine? (no data is saved)"""
import requests

H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E43 data refresh)"}
URLS = {
    "NASA POWER daily": "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=AG"
                        "&longitude=121.0&latitude=14.2&start=20260101&end=20260105&format=JSON",
    "PSA OpenStat API (LFS table)": "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1B/LFS/0021B3FKEI2.px",
    "PSA OpenStat API (fisheries table)": "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/FS/0132E4GVFP1.px",
    "PSA OpenStat LFS folder": "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1B/LFS",
    "PSA website": "https://psa.gov.ph/statistics/labor-force-survey",
    "BSP statistics page": "https://www.bsp.gov.ph/SitePages/Statistics/External.aspx",
    "BSP OF remittances xlsx": "https://www.bsp.gov.ph/Statistics/External/ofw2.xlsx",
}
for name, url in URLS.items():
    try:
        r = requests.get(url, headers=H, timeout=40)
        print(f"{name:36s} HTTP {r.status_code}  {len(r.content)} bytes  {r.headers.get('content-type', '')[:40]}")
    except Exception as e:  # noqa: BLE001
        print(f"{name:36s} ERROR {type(e).__name__}: {str(e)[:120]}")
