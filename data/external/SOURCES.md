# External data sources

Files in this folder are public downloads, stored unmodified and read as data only by
`scripts/ingest_population.py`.

| File | Dataset | Publisher / source | Licence | As of | URL |
|---|---|---|---|---|---|
| `hdx/20211122_location_fce_rrrc_unhcr_population-registration_public.xlsx` | Rohingya Refugees Population by Location at Camp and Union Level - Cox's Bazar (sheet `20211025_Masterlist`: 34 sites with SSID, upazila, union, households, individuals, latitude, longitude) | Inter Sector Coordination Group (ISCG) on HDX; source RRRC-UNHCR family counting / registration | CC0 (public domain) | Population as of 31 Oct 2021 (file dated 22 Nov 2021) | https://data.humdata.org/dataset/site-location-of-rohingya-refugees-in-cox-s-bazar |
| `unhcr/unhcr_rohingya_population_dashboard_2026-06-30.pdf` | Rohingya refugee population dashboard (page 1: totals, age/sex pyramid; page 2: camp/settlement table of families and individuals) | Government of Bangladesh - UNHCR Joint Registration Exercise (DIMA Bangladesh) | Public UNHCR document; no open licence stated. Figures reused with attribution. | 30 Jun 2026 | https://data.unhcr.org/en/documents/download/123174 |

## Host-community wages (not stored here)

| Output | Dataset | Publisher / source | Licence | Period | How obtained |
|---|---|---|---|---|---|
| `data/model/ref_wages_coxsbazar.csv` | Agricultural Wage Statistics: monthly daily wage by district, sex and meal provision | Bangladesh Bureau of Statistics (BBS), public download from the official website (http://www.bbs.gov.bd/) | Public government statistics; reused with attribution | 2017-01 to 2025-12 | Derived by the author. `scripts/ingest_wages.py` reads the author's cleaned monthly district panel (`WAGE_SOURCE`, default `../wage_model/data/Regression_data/`, files `wage_by_month.csv` and `wage_new_2024_2025.csv`), which the author's research pipeline builds from the public BBS files. Only the small derived CSV (Cox's Bazar plus a national median) is committed. If `WAGE_SOURCE` is absent the script skips and the committed CSV is kept. |

Attribution for wages: **"Source: BBS Agricultural Wage Statistics; derived by the author"**. Wages are nominal BDT; no survey microdata are used.

Attribution for the 2026 figures: **"Source: Government of Bangladesh – UNHCR Joint Registration, 30 Jun 2026"**.

Extracted outputs (`data/model/`):
- `dim_camp_population_2021.csv` - 34 sites, 901,703 individuals, 189,747 households (HDX).
- `ref_population_2026.csv` - 35 rows (33 camps incl. Kutupalong RC and Nayapara RC, plus Bhasan Char and "Other"), 1,200,171 individuals, 249,823 families; reconciles exactly with the dashboard totals.
- `ref_demographics_2026.csv` - 6 age groups x 2 sexes, total 1,200,171; under-18 share 52.0%.

Notes: Camp 23 (Shamlapur) appears in the 2021 list but not in the 2026 table. Coordinates in the HDX
file are site points; Camp 4 / Camp 4 Extension and Camp 20 / Camp 20 Extension share coordinates.

> Note: the UNHCR PDF is not committed to this repository (no open licence). Download it from the URL above into `data/external/unhcr/` to re-run `scripts/ingest_population.py`; the derived tables in `data/model/` are committed with attribution.
