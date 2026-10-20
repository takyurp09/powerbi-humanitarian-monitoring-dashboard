// Query: ref_demographics_2026
// Source: pDataFolder & "ref_demographics_2026.csv" (UTF-8, comma-separated, header row)
// REAL reference data (GoB-UNHCR Joint Registration, 30 Jun 2026). Disconnected reference table.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "ref_demographics_2026.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"age_group", type text}, {"sex", type text}, {"individuals", Int64.Type}, {"as_of", type date}
    }, "en-GB")
in
    Typed
