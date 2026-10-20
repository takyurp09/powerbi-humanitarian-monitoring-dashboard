# Build guide

How to assemble `dashboard/HumanitarianMonitoring.pbix` from the files in this repository. Allow about two to three hours for a first build.

## Prerequisites
- Power BI Desktop (Windows, current release). Power BI Service is used only for publishing.
- Optional: Tabular Editor 2 (free) for bulk-importing measures.
- The model CSVs in `data/model/`. Regenerate them with `make all` if needed.

## 1. Load data with Power Query
1. Open Power BI Desktop and select **Transform data**.
2. **Home > Manage parameters > New parameter**: name `pDataFolder`, type Text, value the absolute path to your local `data/model/` folder including the trailing backslash (see `powerquery/pDataFolder.pq`).
3. For each file in `powerquery/` (except `pDataFolder.pq`): **Home > New source > Blank query**, open **Advanced editor**, paste the file contents and rename the query to the file name (for example `fact_results`).
   - Tables: `dim_date`, `dim_camp`, `dim_sector`, `dim_indicator`, `dim_partner`, `fact_results`, `fact_tpm_visits`, and optionally `dq_log`, the real reference tables (`ref_population_2026`, `ref_demographics_2026`, `dim_camp_population_2021`) and `ref_wages_coxsbazar` for page 6.
4. Check that column types match [DATA_DICTIONARY.md](DATA_DICTIONARY.md) and that there are no errors (**View > Column quality**).
5. **Close & apply**.
6. Create the measure host table: **Home > Enter data**, name it `_Measures`, accept the single blank column, then hide that column after measures are added.

## 2. Relationships
In **Model view**, delete any auto-detected relationships and create the following. All are many-to-one (fact to dimension), single cross-filter direction, active.

| From (many) | To (one) | Cardinality | Direction |
|---|---|---|---|
| fact_results[date] | dim_date[date] | Many-to-one | Single |
| fact_results[camp_id] | dim_camp[camp_id] | Many-to-one | Single |
| fact_results[indicator_id] | dim_indicator[indicator_id] | Many-to-one | Single |
| fact_results[partner_id] | dim_partner[partner_id] | Many-to-one | Single |
| dim_indicator[sector_id] | dim_sector[sector_id] | Many-to-one | Single |
| fact_tpm_visits[visit_month] | dim_date[date] | Many-to-one | Single |
| fact_tpm_visits[camp_id] | dim_camp[camp_id] | Many-to-one | Single |
| fact_tpm_visits[partner_id] | dim_partner[partner_id] | Many-to-one | Single |
| fact_tpm_visits[sector_id] | dim_sector[sector_id] | Many-to-one | Single |

`dim_sector` filters `fact_results` through `dim_indicator` (a small snowflake) and `fact_tpm_visits` directly; there is no ambiguous path. `dq_log`, the `ref_*` tables and `dim_camp_population_2021` stay disconnected.

## 3. Model settings
1. Select `dim_date` > **Table tools > Mark as date table**, column `date`.
2. Sort `dim_date[month_name]` by `month_num`.
3. Set `dim_camp[latitude]` and `[longitude]` data categories to Latitude and Longitude; set `camp_name` to Place.
4. Hide all foreign-key columns on fact tables and `visit_month`; set default summarisation to "Don't summarize" for `rating`, `days_to_close`, `latitude`, `longitude`, `population`.
5. Format `children_share` as a percentage.

## 4. Import measures
`dax/measures.dax` contains every measure with its display folder and format string noted in comments.

- **Tabular Editor (recommended)**: **External tools > Tabular Editor**. Either open **C# Script** and create measures from the file, or, simpler, use **File > Open > From DB**, then for each measure **right-click `_Measures` > Create > Measure**, paste the expression, and set *Display Folder* and *Format String* from the comment. Save back to the model (Ctrl+S).
- **DAX query view (Power BI Desktop)**: open **DAX query view**, paste the file and run it to validate. Use **Update model with changes** on the CodeLens above each measure to add it to the model, then set display folders in Model view.
- **Manual**: **New measure** in the `_Measures` table and paste each expression.

Validate by placing `[Achievement %]`, `[Reporting Timeliness %]`, `[DQ Score %]` and `[Closure Rate]` on cards; values should be between 0% and roughly 120%.

## 5. Apply the theme
**View > Themes > Browse for themes** and select `theme/report_theme.json`. It sets a colour-blind-safe palette (Okabe-Ito based), neutral backgrounds and Segoe UI typography.

## 6. Build the pages
Build the five pages described in [DASHBOARD_SPEC.md](DASHBOARD_SPEC.md), starting with the camp detail drill-through page so other pages can target it. Canvas size 1280 x 720 (16:9). Use `assets/wireframe.svg` as the layout reference for the overview page. Configure the mobile layout (**View > Mobile layout**) for each page as described in the spec.

## 7. Save and export screenshots
1. Save as `dashboard/HumanitarianMonitoring.pbix`.
2. For each page, clear slicers to their default state and export an image: **File > Export > Export to PDF** then crop, or use the Windows Snipping Tool at 100% zoom. Save as PNG, approximately 1600 px wide:
   - `assets/overview.png`, `assets/sector.png`, `assets/camp_map.png`, `assets/timeliness_dq.png`, `assets/tpm.png`, `assets/camp_detail.png`.
3. Update the screenshots section of the README if file names change.

## 8. Publish (optional)
1. **Home > Publish**, choose a workspace (My workspace is sufficient for a portfolio).
2. In Power BI Service, open the semantic model settings. Because the source is a local folder, scheduled refresh needs an on-premises data gateway (personal mode); for a static demonstration, leave refresh off.
3. Do not use **Publish to web** for anything other than synthetic or public data. Programme data here are synthetic and population figures are public (keep the source attribution visible), so a public embed is acceptable if desired.

## Troubleshooting
- *File not found*: `pDataFolder` must end with a backslash.
- *Dates parse as text*: confirm the CSVs use ISO dates; the scripts specify culture `en-GB`, which reads ISO correctly.
- *Time intelligence returns blank*: check that `dim_date` is marked as a date table and the relationship to `fact_results[date]` is active.
