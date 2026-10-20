// Query: fact_tpm_visits
// Source: pDataFolder & "fact_tpm_visits.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_tpm_visits.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"visit_id", type text}, {"visit_date", type date}, {"camp_id", type text},
        {"partner_id", type text}, {"sector_id", type text}, {"rating", Int64.Type},
        {"issues_flagged", Int64.Type}, {"issue_category", type text},
        {"followup_status", type text}, {"days_to_close", Int64.Type}
    }, "en-GB"),
    // Month key for the relationship to dim_date (one row per month)
    WithMonth = Table.AddColumn(Typed, "visit_month", each Date.StartOfMonth([visit_date]), type date),
    Result    = WithMonth
in
    Result
