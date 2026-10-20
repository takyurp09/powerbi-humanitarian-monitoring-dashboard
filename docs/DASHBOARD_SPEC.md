# Dashboard specification

Six report pages plus one drill-through page. Canvas 1280 x 720. Measures refer to `dax/measures.dax`; fields refer to [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Global conventions
- **Header band** on every page: dynamic title measure (left), data note `[Data Note]` (small, grey), and slicers (right).
- **Standard slicers** (synced across pages via **View > Sync slicers**): `dim_date[fiscal_label]` (between/range or dropdown), `dim_sector[sector_name]`, `dim_camp[upazila]`, `dim_partner[partner_name]`.
- **Status colours** (colour-blind safe, Okabe-Ito): On track `#0072B2` (blue), At risk `#E69F00` (orange), Off track `#D55E00` (vermilion), No data `#9E9E9E`. Status is always shown with a text label or icon as well as colour.
- **Conditional formatting**: wherever achievement is coloured, use *Format style: Field value* based on `[Status Colour]`.
- **Accessibility**: every visual has alt text (Format > General > Alt text) describing what it shows and the key takeaway, ideally a dynamic measure; tab order set via **View > Selection** pane; minimum font size 10 pt; contrast at least 4.5:1 for text; no information carried by colour alone.
- **Tooltips**: a shared report-page tooltip `TT Camp` (320 x 240) showing `[Achievement %]`, `[Status Label]`, `[Reporting Timeliness %]`, `[DQ Score %]`, `[TPM Visits]` and a small monthly sparkline of `[Achievement %]`.

## Page 1. Executive overview
**Purpose**: one-screen answer to "are we on track, where are the problems, and can we trust the data?" for senior management.

| Visual | Type | Fields and measures |
|---|---|---|
| Title | Card (new) / text box | `[Title - Overview]` |
| KPI row | 5 cards | `[Achievement %]` (subtitle `[KPI Subtitle - Achievement]`), `[Children reached]`, `[Reporting Timeliness %]`, `[DQ Score %]`, `[Closure Rate]` |
| Monthly trend | Line chart | X: `dim_date[date]` (month); Y: `[Achievement %]`, `[Rolling 3M Achievement %]`; constant line at 90% labelled "On-track threshold" |
| Sector status | Clustered bar chart | Y: `dim_sector[sector_name]`; X: `[Achievement %]`; bar colour by `[Status Colour]`; data labels on |
| Camp map | Map (bubble) | Latitude/longitude: `dim_camp`; size: `dim_camp[population]`; colour: `[Status Colour]`; tooltip page `TT Camp` |
| Camp table | Table | `dim_camp[camp_name]`, `dim_camp[upazila]`, `[Achievement %]`, `[Status Label]`, `[Reporting Timeliness %]`, `[DQ Score %]`, `[Open Follow-ups > 30 days]` |

- **Conditional formatting**: `[Achievement %]` column background by `[Status Colour]`; `[Open Follow-ups > 30 days]` font colour `#D55E00` when > 0; timeliness and DQ with data bars.
- **Drill-through**: right-click a camp in the map or table to open *Camp detail*.
- **Mobile layout**: title, KPI cards stacked 2 per row, sector bar chart, camp table (map omitted).

## Page 2. Sector and indicator performance
**Purpose**: indicator-level performance for sector leads; identify off-track indicators and partners.

| Visual | Type | Fields and measures |
|---|---|---|
| Title | Card | `[Title - Sector]` |
| Indicator matrix | Matrix | Rows: `dim_sector[sector_name]` > `dim_indicator[indicator_name]`; Values: `[Total Target]`, `[Total Achieved]`, `[Achievement %]`, `[Gap to Target]`, `[Achievement % MoM Change]`, `[Status Label]` |
| Achievement by partner | Bar chart | Y: `dim_partner[partner_name]`; X: `[Achievement %]`; colour `[Status Colour]`; legend off |
| Target vs achieved trend | Line and clustered column | X: month; columns: `[Target (count indicators)]`, `[Achieved (count indicators)]`; line: `[Achievement %]` |
| Year comparison | Clustered column | X: `dim_date[month_name]`; values: `[Achieved (count indicators)]`, `[Achieved Same Period Last Year]` |
| Off-track count | Card | `[Indicators off track]` |

- **Slicers**: standard set plus `dim_indicator[unit]` and `fact_results[sex]`.
- **Conditional formatting**: matrix `[Achievement %]` background by `[Status Colour]`; `[Achievement % MoM Change]` icons (up/down arrows, with text label).
- **Note**: totals of `[Total Target]` across mixed units are not meaningful; show the matrix totals only for `[Achievement %]` (turn off subtotals for target and achieved at sector level, or rely on the count-indicator measures).
- **Mobile layout**: title, off-track card, matrix (collapsed to sector level), partner bar chart.

## Page 3. Camp map and equity
**Purpose**: geographic coverage and equity; which camps lag, and are girls and women reached proportionately?

| Visual | Type | Fields and measures |
|---|---|---|
| Camp map | Azure Map or Map (bubble) | Lat/long from `dim_camp`; size `[Achieved (count indicators)]`; colour `[Status Colour]`; tooltip `TT Camp` |
| Female share by camp | Bar chart | Y: `dim_camp[camp_name]`; X: `[Female share %]`; constant line at 50% |
| Sex breakdown | 100% stacked bar | Y: `dim_sector[sector_name]`; X: `[Achieved (count indicators)]`; legend: `fact_results[sex]` |
| Reach vs child population | Scatter | Details: `dim_camp[camp_name]`; X: `dim_camp[children_population]` (sum); Y: `[Children reached]`; size: `dim_camp[population]`; colour: `dim_camp[upazila]` |
| Upazila summary | Multi-row card | `[Achievement %]`, `[Female share %]`, `[Camps off track]` by `dim_camp[upazila]` |

- **Slicers**: standard set plus `fact_results[sex]`.
- **Conditional formatting**: `[Female share %]` bars orange `#E69F00` when below 45%.
- **Drill-through**: camp map and bar chart to *Camp detail*.
- **Mobile layout**: upazila summary, female share bar chart, sex breakdown; map available in landscape only.

## Page 4. Reporting timeliness and data quality
**Purpose**: monitor partner reporting discipline and data quality so that results can be trusted.

| Visual | Type | Fields and measures |
|---|---|---|
| KPI cards | 4 cards | `[Reporting Timeliness %]`, `[Late Reports]`, `[DQ Score %]`, `[DQ Issues]` |
| Timeliness trend | Line chart | X: month; Y: `[Reporting Timeliness %]`, `[DQ Score %]`; constant line at 90% |
| DQ issues by type | Stacked column | X: month; Y: `[DQ Issues]`; legend: `fact_results[dq_flag]` (filter out "OK") |
| Partner scorecard | Table | `dim_partner[partner_name]`, `dim_partner[partner_type]`, `[Reporting Timeliness %]`, `[Late Reports]`, `[Avg Reporting Lag (days)]`, `[DQ Score %]`, `[DQ Issues - Missing]`, `[DQ Issues - Outlier]`, `[DQ Issues - Inconsistent]` |
| Camp x month heatmap | Matrix | Rows: `dim_camp[camp_name]`; columns: `dim_date[fiscal_label]`; values: `[Reporting Timeliness %]` with background gradient |
| Cleaning log | Table | `dq_log[rule]`, `dq_log[rows_affected]` (optional) |

- **Conditional formatting**: scorecard percentages by rules (>= 90% blue, 70-89% orange, < 70% vermilion) with icons; heatmap uses a single-hue sequential blue scale (colour-blind safe).
- **Mobile layout**: KPI cards, timeliness trend, partner scorecard (key columns only).

## Page 5. Third-party monitoring follow-up
**Purpose**: track issues raised by third-party monitors and whether partners close them promptly.

| Visual | Type | Fields and measures |
|---|---|---|
| Title | Card | `[Title - TPM]` |
| KPI cards | 5 cards | `[TPM Visits]`, `[Avg Rating]`, `[Issues Flagged]`, `[Closure Rate]`, `[Avg Days to Close]` |
| Overdue alert | Card | `[Open Follow-ups > 30 days]`, font colour `#D55E00` when > 0 |
| Issues by category | Bar chart | Y: `fact_tpm_visits[issue_category]`; X: `[Issues Flagged]`; `[Safeguarding Issues]` highlighted |
| Visits and closure trend | Line and column | X: month; columns: `[TPM Visits]`; line: `[Closure Rate]` |
| Rating distribution | Column chart | X: `fact_tpm_visits[rating]`; Y: `[TPM Visits]` |
| Partner follow-up table | Table | `dim_partner[partner_name]`, `[Visits with Issues]`, `[Follow-ups Open]`, `[Closure Rate]`, `[Avg Days to Close]`, `[Open Follow-ups > 30 days]` |
| Open items list | Table | `fact_tpm_visits[visit_id]`, `visit_date`, `dim_camp[camp_name]`, `dim_sector[sector_name]`, `issue_category`, `issues_flagged`; visual filter `followup_status = "Open"` |

- **Slicers**: standard set plus `fact_tpm_visits[issue_category]` and `fact_tpm_visits[followup_status]`.
- **Conditional formatting**: `[Closure Rate]` icons; `[Avg Days to Close]` data bars; overdue counts in vermilion.
- **Mobile layout**: overdue alert, KPI cards, partner follow-up table.

## Page 6. Host community context
**Purpose**: place the camp response next to conditions in the host district. Shows the Cox's Bazar agricultural wage trend (real BBS data) alongside the real camp population, so readers see the local labour market the response operates in.

| Visual | Type | Fields and measures |
|---|---|---|
| Title | Text box | "Host community context: Cox's Bazar agricultural wages" |
| KPI cards | 4 cards | `[Host Wage (median daily, BDT)]`, `[Wage YoY %]`, `[Host vs national wage gap %]`, `[Camp Population (real)]` |
| Wage trend | Line chart | X: `ref_wages_coxsbazar[date]` (month); Y: `[Host Wage (median daily, BDT)]`, `[National Wage (median daily, BDT)]`; legend off, series labelled at line ends |
| Wage by sex | Line chart | X: `ref_wages_coxsbazar[date]`; Y: `[Host Wage (median daily, BDT)]`; legend: `ref_wages_coxsbazar[sex]` |
| Camp population | Column chart | X: `dim_camp_population_2021[as_of]` and `ref_population_2026[as_of]` (two snapshots: 901,703 in Oct 2021; 1,200,171 in Jun 2026); Y: sum of individuals. Two points only, so columns, not a line |
| Meal provision | Clustered bar | Y: `ref_wages_coxsbazar[meals]`; X: `[Host Wage (median daily, BDT)]`, `[National Wage (median daily, BDT)]` |
| Source note | Text box / card | `[Wage Source Note]` |

- **Slicers (page level, not synced)**: `ref_wages_coxsbazar[sex]`, `ref_wages_coxsbazar[meals]` (single select, default "No meals"), year range on `ref_wages_coxsbazar[date]`. The standard programme slicers do not filter this page because the wage table is disconnected.
- **Interpretation note (shown on the page)**: "Descriptive context only. Wages are nominal and not adjusted for inflation; camp population has only two snapshots. The page does not claim that the refugee presence caused any change in wages." Do not add trend lines or correlation figures.
- **Gaps**: months that BBS did not publish are left blank; turn off "Show items with no data" and do not interpolate.
- **Mobile layout**: KPI cards, wage trend, source note.

## Drill-through page. Camp detail (hidden)
- **Drill-through field**: `dim_camp[camp_name]`; *Keep all filters* on; back button top left.
- **Visuals**: `[Title - Camp Detail]`; cards for `dim_camp[population]`, `dim_camp[children_share]`, `[Achievement %]`, `[Reporting Timeliness %]`, `[DQ Score %]`, `[TPM Visits]`; line chart of `[Achievement %]` by month; matrix of indicators with `[Achievement %]` and `[Status Label]`; table of TPM visits for the camp.
- **Alt text example**: "Line chart of monthly achievement for the selected camp against the 90% on-track threshold."
