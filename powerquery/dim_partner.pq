// Query: dim_partner
// Source: pDataFolder & "dim_partner.csv" (UTF-8, comma-separated, header row)
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_partner.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"partner_id", type text}, {"partner_name", type text}, {"partner_type", type text}
    }, "en-GB"),
    Result   = Typed
in
    Result
