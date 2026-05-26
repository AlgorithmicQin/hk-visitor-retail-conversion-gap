# Raw Data Acquisition

This repository does not redistribute raw official datasets. To reproduce the project from a public clone, obtain the source data from official Census and Statistics Department, HKSAR sources and save the raw payloads locally before running the preprocessing script.

## Required Official Sources

Publisher: Census and Statistics Department, HKSAR

Coverage used in this pilot: `201801` to `202603`

Required tables:

- Visitor Arrivals Table `650-80001`
- Retail Sales Table `620-67002`

During pilot setup, the C&SD web-table CSV download links returned HTML pages rather than direct CSV data. The project therefore uses C&SD API JSON responses saved locally, then preprocesses those JSON payloads into normalized CSV files.

The saved payload metadata confirms these table parameters:

| Dataset | C&SD table | Period requested | Series used | API help page |
| --- | --- | --- | --- | --- |
| Visitor arrivals | `650-80001` | `201801` to `202612` | `VIS_ARR` | `https://www.censtatd.gov.hk/en/web_table.html?id=650-80001&api_popup=1` |
| Retail sales by outlet category | `620-67002` | `201801` to `202612` | `VAL_RS` | `https://www.censtatd.gov.hk/en/web_table.html?id=620-67002&api_popup=1` |

The analysis uses data available through `202603`; later requested periods are ignored if unavailable in the official response.

## Expected Local Raw Files

Save the official C&SD API JSON payloads as:

```text
data/raw/visitor_arrivals_real.csv
data/raw/retail_sales_real.csv
```

Despite the `.csv` extension, these files are JSON payloads returned by the C&SD API. They are treated as JSON by `src/preprocess_censd_json.py`.

Raw official payloads are ignored by Git and should remain local.

## Preprocessing Outputs

Run:

```bash
python src/preprocess_censd_json.py
```

The script converts the raw JSON payloads into normalized CSV files used by the analysis pipeline:

```text
data/raw/visitor_arrivals.csv
data/raw/retail_sales.csv
```

The normalized visitor file contains:

- `Month`
- `Total arrivals`

The normalized retail file contains:

- `Month`
- `Retail category`
- `Sales value`

## Endpoint Notes

The exact API request method is documented by C&SD through the API help pages linked above. See `docs/data_sources.md` for the current project source notes and column expectations.

Do not enter values by hand or create replacement files manually. If the C&SD API changes, update the acquisition notes before changing the analysis pipeline.
