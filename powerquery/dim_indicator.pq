// Query: dim_indicator
// Source: pDataFolder & "dim_indicator.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_indicator.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"indicator_id", type text}, {"sector_id", type text}, {"indicator_name", type text},
        {"unit", type text}, {"aggregation", type text}, {"higher_is_better", type logical}
    }, "en-GB"),
    Result   = Table.TransformColumns(Typed, {{"aggregation", Text.Lower, type text}})
in
    Result
