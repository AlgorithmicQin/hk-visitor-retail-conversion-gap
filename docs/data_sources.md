# Data Sources

This pilot uses manually downloaded monthly Hong Kong datasets. Do not enter values by hand and do not fabricate missing periods.

Accepted raw file types:

- `.csv`
- `.xlsx`
- `.xls`

The recovery notebook discovers the first matching file by dataset stem in this order: `.csv`, `.xlsx`, `.xls`.

Note: C&SD web table download links returned HTML pages rather than direct CSV data during pilot setup. For C&SD visitor arrivals and retail sales, the pilot uses C&SD API POST JSON responses saved in `data/raw/*_real.csv`, then preprocesses those JSON payloads into normalized CSV files for the notebooks.

## 1. Monthly Visitor Arrivals

Expected raw placement:

```text
data/raw/visitor_arrivals.csv
data/raw/visitor_arrivals.xlsx
data/raw/visitor_arrivals.xls
```

Minimum required fields after mapping:

| Standard field | Meaning | Example raw column names |
| --- | --- | --- |
| `month` | Monthly period | `Month`, `Date`, `Period`, `Year Month` |
| `visitor_arrivals` | Total visitor arrivals | `Total arrivals`, `Visitors`, `Arrivals` |

Optional fields:

- `source_market`
- `arrival_mode`
- `overnight_same_day`

Example mapping:

```python
visitor_column_map = {
    "Month": "month",
    "Total arrivals": "visitor_arrivals",
}
```

## 2. Monthly Retail Sales by Category

Expected raw placement:

```text
data/raw/retail_sales.csv
data/raw/retail_sales.xlsx
data/raw/retail_sales.xls
```

Minimum required fields after mapping:

| Standard field | Meaning | Example raw column names |
| --- | --- | --- |
| `month` | Monthly period | `Month`, `Date`, `Period`, `Year Month` |
| `retail_sales_value` | Retail sales value | `Sales value`, `Value`, `Retail sales` |

Recommended category field:

| Standard field | Meaning | Example raw column names |
| --- | --- | --- |
| `retail_category` | Retail category or trade group | `Category`, `Trade`, `Retail outlet type` |

For the first pilot, aggregate retail categories only after checking the source definitions are stable over time.

Example mapping:

```python
retail_column_map = {
    "Month": "month",
    "Sales value": "retail_sales_value",
    # "Category": "retail_category",
}
```

## 3. Monthly Hotel Occupancy / Room Rate

Expected raw placement:

```text
data/raw/hotel_performance.csv
data/raw/hotel_performance.xlsx
data/raw/hotel_performance.xls
```

Minimum required fields after mapping:

| Standard field | Meaning | Example raw column names |
| --- | --- | --- |
| `month` | Monthly period | `Month`, `Date`, `Period`, `Year Month` |

Optional hotel indicator fields after mapping:

| Standard field | Meaning | Example raw column names |
| --- | --- | --- |
| `hotel_occupancy_rate` | Occupancy rate | `Occupancy`, `Occupancy rate`, `Room occupancy rate` |
| `hotel_room_rate` | Average achieved hotel room rate | `Room rate`, `Average room rate`, `ARR` |

At least one hotel indicator column is needed for the visitor-hotel gap. The pilot can run with occupancy only, room rate only, or both.

Example mapping:

```python
hotel_column_map = {
    "Month": "month",
    "Occupancy rate": "hotel_occupancy_rate",
    "Average room rate": "hotel_room_rate",
}
```

If the hotel file contains only one indicator, leave both mappings in place if the raw column names are plausible. Missing optional mapped hotel columns are ignored by the loader, and the notebook reports which hotel indicators are unavailable.

## Column Mapping Instructions

In the notebooks, define a mapping from raw column names to standard names.

```python
visitor_column_map = {
    "Month": "month",
    "Total arrivals": "visitor_arrivals",
}
```

Then load with:

```python
from src.data_loader import load_monthly_dataset

visitors = load_monthly_dataset(
    visitor_file,
    column_map=visitor_column_map,
    required_columns=["month", "visitor_arrivals"],
)
```

Date fields are parsed with `pandas.to_datetime()` and then standardized to month-start timestamps. The loader also accepts compact `YYYYMM` values such as `201801`.

## Source Log

Use this table while collecting raw files.

| Dataset | Source URL | Download date | Raw file name | Notes |
| --- | --- | --- | --- | --- |
| Visitor arrivals |  |  |  |  |
| Retail sales |  |  |  |  |
| Hotel performance |  |  |  |  |
