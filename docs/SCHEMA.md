# Data model (shared contract)

Star schema for a humanitarian programme performance and third-party monitoring (TPM) dashboard, modelled on a multi-sector child-focused response in Cox's Bazar camps. **Camp reference data are real; programme data are synthetic.** `dim_camp` (camp names, upazila, union, coordinates, population, families) and the `ref_*` / `dim_camp_population_2021` tables come from public sources (host-community wages: BBS, via `scripts/ingest_wages.py`) (see `data/external/SOURCES.md`, built by `scripts/ingest_population.py`). Programme results, partners and TPM visits are synthetic (`scripts/generate_data.py`, seed 2026), with count targets scaled to real camp population (children indicators to children population).

Period: monthly, 2025-01 to 2026-06 (18 months). Files are CSV, UTF-8, comma-separated, ISO dates.

## Dimensions (data/model/)
| File | Columns |
|---|---|
| dim_date.csv | date (first of month, YYYY-MM-DD), year, quarter (Q1..Q4), month_num, month_name (Jan..), fiscal_label ("2025-01") |
| dim_camp.csv | camp_id (C01..C24, assigned in natural camp order), camp_name (real, e.g. "Camp 1E", "Camp 4 Extension"), upazila (Ukhia or Teknaf), union, latitude, longitude (real HDX site points), population (int, real), families (int, real), children_share (0-1, national under-18 share from 2026 dashboard), population_source, population_as_of (YYYY-MM-DD). The 24 most populous camps in the 2026 table that also have an HDX site row. |
| dim_sector.csv | sector_id (S1..S5), sector_name (Education, Child Protection, WASH, Health, Nutrition) |
| dim_indicator.csv | indicator_id (I01..I15, 3 per sector), sector_id, indicator_name, unit ("people","children","facilities","%"), aggregation ("sum" or "avg"), higher_is_better (TRUE/FALSE) |
| dim_partner.csv | partner_id (P01..P10), partner_name ("Partner A".."Partner J"), partner_type (National NGO, International NGO, Government) |

## Reference tables (data/model/, real, disconnected)
| File | Columns |
|---|---|
| dim_camp_population_2021.csv | camp_ssid, camp_name, site_alias, upazila, union, households, individuals, latitude, longitude, as_of (2021-10-31) |
| ref_population_2026.csv | camp_name, families, individuals, as_of (2026-06-30); sums to 1,200,171 / 249,823 |
| ref_demographics_2026.csv | age_group (Below 1, 1-4, 5-11, 12-17, 18-59, 60+), sex, individuals, as_of; sums to 1,200,171 |
| ref_wages_coxsbazar.csv | date (first of month, 2017-01 to 2025-12), district ("Cox's Bazar" or "Bangladesh (national median)"), sex (Female/Male), meals ("No meals","1 meal","2 meals","3 meals"), daily_wage_bdt (int, nominal), source. Host-community agricultural wage context from BBS Agricultural Wage Statistics (public), derived by the author (`scripts/ingest_wages.py`). Key: date x district x sex x meals. Months missing in the BBS series are absent, not zero. |

## Facts (data/model/)
| File | Grain | Columns |
|---|---|---|
| fact_results.csv | month x camp x indicator x partner x sex | date, camp_id, indicator_id, partner_id, sex (Female/Male), target, achieved, reported_date, is_late (TRUE if reported after the 10th of following month), dq_flag ("OK","Missing","Outlier","Inconsistent") |
| fact_tpm_visits.csv | one row per TPM visit | visit_id (V00001..), visit_date (YYYY-MM-DD), camp_id, partner_id, sector_id, rating (1=Poor..4=Good), issues_flagged (int), issue_category ("Quality","Access","Safeguarding","Supplies","Reporting"), followup_status ("Closed","Open"), days_to_close (int, blank if Open) |

## Raw layer (data/raw/)
Messy versions written by the generator to demonstrate cleaning: `raw_results_partner_reports.csv` (inconsistent camp name spellings like "camp-1e"/"Camp 1 E", mixed date formats, some blank achieved values, duplicated rows) and `raw_tpm_visits.csv`. `scripts/clean_data.py` turns raw into model/ and writes `data/model/dq_log.csv` (rule, rows_affected).

## Key business definitions (used by DAX and docs)
- Achievement % = SUM(achieved) / SUM(target) for sum-indicators; for avg-indicators use AVERAGE.
- On-track status: >=90% Green, 70-89% Amber, <70% Red.
- Reporting timeliness % = share of result rows with is_late = FALSE.
- Data quality score % = share of rows with dq_flag = "OK".
- TPM follow-up closure rate = Closed / total visits with issues_flagged > 0.
- Average days to close = mean days_to_close over Closed visits with issues_flagged > 0.
- Children population = population x children_share; Coverage % = average monthly achieved (children-unit count indicators) / children population.
