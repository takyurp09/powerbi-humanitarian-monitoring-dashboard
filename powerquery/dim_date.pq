// Query: dim_date
// Source: pDataFolder & "dim_date.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date", type date}, {"year", Int64.Type}, {"quarter", type text},
        {"month_num", Int64.Type}, {"month_name", type text}, {"fiscal_label", type text}
    }, "en-GB"),
    Result   = Table.Sort(Typed, {{"date", Order.Ascending}})
in
    Result
