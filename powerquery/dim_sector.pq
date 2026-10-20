// Query: dim_sector
// Source: pDataFolder & "dim_sector.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_sector.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"sector_id", type text}, {"sector_name", type text}
    }, "en-GB"),
    Result   = Typed
in
    Result
