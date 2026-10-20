// Query: dim_camp
// Source: pDataFolder & "dim_camp.csv" (UTF-8, comma-separated, header row)
// population/families/coordinates are REAL (GoB-UNHCR 2026; HDX 2021), see data/external/SOURCES.md
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_camp.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"camp_id", type text}, {"camp_name", type text}, {"upazila", type text}, {"union", type text},
        {"latitude", type number}, {"longitude", type number},
        {"population", Int64.Type}, {"families", Int64.Type}, {"children_share", type number},
        {"population_source", type text}, {"population_as_of", type date}
    }, "en-GB"),
    // Derived column for equity and per-capita views
    Result   = Table.AddColumn(Typed, "children_population", each Number.Round([population] * [children_share]), Int64.Type)
in
    Result
