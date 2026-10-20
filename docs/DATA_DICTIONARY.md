# Data dictionary

All tables live in `data/model/` as UTF-8 CSV files and are loaded through the Power Query scripts in `powerquery/`. The binding contract is [SCHEMA.md](SCHEMA.md); this document adds Power BI data types and descriptions. Camp population data are real (see `data/external/SOURCES.md`); programme results, partners and TPM visits are synthetic.

Power BI types: Text, Whole number (Int64), Decimal number, Date, True/False.

## dim_date
One row per month, January 2025 to June 2026. Marked as the date table on `date`.

| Column | Type | Description |
|---|---|---|
| date | Date | First day of the month (key). |
| year | Whole number | Calendar year. |
| quarter | Text | Calendar quarter, "Q1" to "Q4". |
| month_num | Whole number | Month number 1-12; sort key for `month_name`. |
| month_name | Text | Abbreviated month name ("Jan"). Sort by `month_num`. |
| fiscal_label | Text | Period label in "YYYY-MM" form. |

## dim_camp
One row per camp (24 camps): the most populous camps in the GoB-UNHCR 30 Jun 2026 table that also appear in the HDX 2021 site list (Bhasan Char and "Other" excluded).

| Column | Type | Description |
|---|---|---|
| camp_id | Text | Camp key, "C01" to "C24", assigned in natural camp order. |
| camp_name | Text | Real camp name as published (e.g. "Camp 1E", "Camp 4 Extension"). |
| upazila | Text | Sub-district from HDX: Ukhia or Teknaf. |
| union | Text | Union from HDX (e.g. Palong Khali, Nhilla). |
| latitude | Decimal number | Real site latitude (HDX 2021). Data category: Latitude. |
| longitude | Decimal number | Real site longitude (HDX 2021). Data category: Longitude. |
| population | Whole number | Real individuals: 2026 GoB-UNHCR figure, else HDX 2021 figure. |
| families | Whole number | Real families (2026) or households (2021), matching `population`. |
| children_share | Decimal number | National under-18 share from the 2026 dashboard (0.520), applied to every camp. Format as percentage. |
| population_source | Text | "GoB-UNHCR Joint Registration (dashboard)" or "RRRC-UNHCR family counting (HDX)". |
| population_as_of | Date | 2026-06-30 or 2021-10-31. |
| children_population | Whole number | Derived in Power Query: round(population x children_share). |

## dim_camp_population_2021 (real, disconnected)
HDX / ISCG site list, RRRC-UNHCR family counting, CC0, as of 31 Oct 2021 (34 sites).

| Column | Type | Description |
|---|---|---|
| camp_ssid | Text | Site ID (e.g. "CXB-201"). |
| camp_name | Text | Camp name. |
| site_alias | Text | Local site name, may be blank. |
| upazila, union | Text | Administrative units. |
| households | Whole number | Households counted. |
| individuals | Whole number | Individuals counted. |
| latitude, longitude | Decimal number | Site point coordinates. |
| as_of | Date | 2021-10-31. |

## ref_population_2026 (real, disconnected)
GoB-UNHCR Joint Registration, 30 Jun 2026, page 2 camp table (35 rows incl. Bhasan Char and "Other").

| Column | Type | Description |
|---|---|---|
| camp_name | Text | Camp / settlement name. |
| families | Whole number | Registered families. |
| individuals | Whole number | Registered individuals. |
| as_of | Date | 2026-06-30. |

## ref_demographics_2026 (real, disconnected)
National age/sex pyramid, GoB-UNHCR Joint Registration, 30 Jun 2026 (12 rows).

| Column | Type | Description |
|---|---|---|
| age_group | Text | Below 1, 1-4, 5-11, 12-17, 18-59, 60+. |
| sex | Text | Female or Male. |
| individuals | Whole number | Individuals in the group. |
| as_of | Date | 2026-06-30. |

## ref_wages_coxsbazar (real, disconnected)
Host-community context. Nominal daily agricultural wage (BDT) from the BBS Agricultural Wage Statistics, a public download from the BBS website. Built by `scripts/ingest_wages.py` from the author's cleaned monthly district panel (the author's research pipeline, rebuilt from the public BBS files). Cox's Bazar district plus the median across the 64 districts. 2017-01 to 2025-12; months that BBS did not report are absent.

| Column | Type | Description |
|---|---|---|
| date | Date | First day of the month. |
| district | Text | "Cox's Bazar" or "Bangladesh (national median)" (median of district medians for the same month, sex and meals). |
| sex | Text | Female or Male (sex of the worker). |
| meals | Text | Meals provided by the employer per workday: "No meals", "1 meal", "2 meals", "3 meals". |
| daily_wage_bdt | Whole number | Nominal daily wage in Bangladeshi taka (not deflated). |
| source | Text | "BBS Agricultural Wage Statistics (public); derived by author". |

Note: "No meals" is used instead of "None" so that CSV readers do not parse it as missing.

## dim_sector
| Column | Type | Description |
|---|---|---|
| sector_id | Text | Sector key, "S1" to "S5". |
| sector_name | Text | Education, Child Protection, WASH, Health or Nutrition. |

## dim_indicator
Three indicators per sector (15 in total).

| Column | Type | Description |
|---|---|---|
| indicator_id | Text | Indicator key, "I01" to "I15". |
| sector_id | Text | Foreign key to `dim_sector`. |
| indicator_name | Text | Indicator description. |
| unit | Text | "people", "children", "facilities" or "%". |
| aggregation | Text | "sum" (counts, additive) or "avg" (rates, averaged). Drives `[Achievement %]`. |
| higher_is_better | True/False | FALSE where a lower value is the desired direction; the achievement ratio is then inverted. |

## dim_partner
| Column | Type | Description |
|---|---|---|
| partner_id | Text | Partner key, "P01" to "P10". |
| partner_name | Text | Anonymised partner name, "Partner A" to "Partner J". |
| partner_type | Text | National NGO, International NGO or Government. |

## fact_results
Grain: month x camp x indicator x partner x sex.

| Column | Type | Description |
|---|---|---|
| date | Date | Reporting month (first of month). Foreign key to `dim_date`. |
| camp_id | Text | Foreign key to `dim_camp`. |
| indicator_id | Text | Foreign key to `dim_indicator`. |
| partner_id | Text | Foreign key to `dim_partner`. |
| sex | Text | Female or Male. |
| target | Decimal number | Planned value for the month. |
| achieved | Decimal number | Reported value for the month. |
| reported_date | Date | Date the partner report was submitted. |
| is_late | True/False | TRUE if submitted after the 10th of the following month. |
| dq_flag | Text | Data quality flag: "OK", "Missing", "Outlier" or "Inconsistent". |

## fact_tpm_visits
Grain: one row per third-party monitoring visit.

| Column | Type | Description |
|---|---|---|
| visit_id | Text | Visit key, "V00001" onwards. |
| visit_date | Date | Date of the visit. |
| visit_month | Date | Derived in Power Query: first day of `visit_date`'s month. Foreign key to `dim_date`. |
| camp_id | Text | Foreign key to `dim_camp`. |
| partner_id | Text | Foreign key to `dim_partner`. |
| sector_id | Text | Foreign key to `dim_sector`. |
| rating | Whole number | Overall rating, 1 = Poor to 4 = Good. |
| issues_flagged | Whole number | Number of issues raised during the visit. |
| issue_category | Text | Quality, Access, Safeguarding, Supplies or Reporting. |
| followup_status | Text | Closed or Open. |
| days_to_close | Whole number | Days from visit to follow-up closure; blank when Open. |

## dq_log (optional, disconnected)
Written by `scripts/clean_data.py`.

| Column | Type | Description |
|---|---|---|
| rule | Text | Cleaning rule applied (e.g. camp name standardisation, deduplication). |
| rows_affected | Whole number | Number of raw rows affected by the rule. |

## Business definitions
- **Achievement %**: SUM(achieved) / SUM(target) for sum-indicators; AVERAGE(achieved) / AVERAGE(target) for avg-indicators; indicator ratios are averaged with equal weight when several indicators are in context.
- **Status**: >= 90% On track (green band), 70-89% At risk (amber band), < 70% Off track (red band).
- **Reporting timeliness %**: share of result rows with `is_late` = FALSE.
- **Data quality score %**: share of result rows with `dq_flag` = "OK".
- **TPM closure rate**: Closed visits / visits with `issues_flagged` > 0.
- **Average days to close**: mean `days_to_close` over Closed visits with `issues_flagged` > 0.
- **Children population**: `population` x `children_share` (real population, national under-18 share).
- **Reach per 1,000 children**: average monthly children reached / children population x 1,000.
- **Host wage (median daily, BDT)**: median of `daily_wage_bdt` for Cox's Bazar in context; filter `meals` to one value (default "No meals") for a like-for-like series.
- **Host vs national wage gap %**: Cox's Bazar median / national median - 1, same month, sex and meals filters.
- **Coverage %**: average monthly achieved for children-unit count indicators / children population; read per indicator.
