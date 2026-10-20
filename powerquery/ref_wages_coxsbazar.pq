// Query: ref_wages_coxsbazar
// Source: pDataFolder & "ref_wages_coxsbazar.csv" (UTF-8, comma-separated, header row)
// REAL reference data: BBS Agricultural Wage Statistics (public), Cox's Bazar district and
// national median across 64 districts, nominal daily wage in BDT, 2017-2025. Derived by the
// author from the public BBS files (scripts/ingest_wages.py). Disconnected reference table;
// relate ref_wages_coxsbazar[date] to dim_date[date] only if dim_date is extended to 2017.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "ref_wages_coxsbazar.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date", type date}, {"district", type text}, {"sex", type text}, {"meals", type text},
        {"daily_wage_bdt", Int64.Type}, {"source", type text}
    }, "en-GB")
in
    Typed
