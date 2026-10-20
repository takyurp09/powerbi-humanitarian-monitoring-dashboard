// Query: dim_camp_population_2021
// Source: pDataFolder & "dim_camp_population_2021.csv" (UTF-8, comma-separated, header row)
// REAL reference data (HDX / RRRC-UNHCR, CC0, as of 2021-10-31). Disconnected reference table.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_camp_population_2021.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"camp_ssid", type text}, {"camp_name", type text}, {"site_alias", type text}, {"upazila", type text},
        {"union", type text}, {"households", Int64.Type}, {"individuals", Int64.Type},
        {"latitude", type number}, {"longitude", type number}, {"as_of", type date}
    }, "en-GB")
in
    Typed
