// Query: dq_log
// Optional: cleaning log written by scripts/clean_data.py (disconnected table).
// Source: pDataFolder & "dq_log.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dq_log.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"rule", type text}, {"rows_affected", Int64.Type}
    }, "en-GB"),
    Result   = Typed
in
    Result
