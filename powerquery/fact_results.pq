// Query: fact_results
// Source: pDataFolder & "fact_results.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_results.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date", type date}, {"camp_id", type text}, {"indicator_id", type text},
        {"partner_id", type text}, {"sex", type text}, {"target", type number},
        {"achieved", type number}, {"reported_date", type date},
        {"is_late", type logical}, {"dq_flag", type text}
    }, "en-GB"),
    Result   = Table.TransformColumns(Typed, {{"dq_flag", Text.Trim, type text}})
in
    Result
