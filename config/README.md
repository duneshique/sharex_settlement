# Campaign Classification Rules Configuration

This directory contains the campaign classification rules extracted from the Share X Settlement Excel file.

## Files

### campaign_rules.json
The primary configuration file containing all campaign classification rules, ad target mappings, exchange rates, and course count information.

**Key Contents:**
- Classification rules for 5 ad targets (SHARE X, PLUS X, BKID, BLSN, SANDOLL)
- Campaign pattern matching rules for automatic classification
- 3 media channels (Google, Meta, Naver)
- 6 historical exchange rates (USD to KRW)
- Course count configuration (PLUS X: 24, Union: 15, Total: 39)
- 21 unique campaign names with pattern matching

**File Size:** 3,812 bytes
**Format:** UTF-8 JSON
**Last Updated:** 2026-02-09

## Usage

### Loading the Configuration

```python
import json

with open('campaign_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)
```

### Accessing Target Information

```python
# Get classification type for a target
share_x_rule = rules['classification_rules']['target_mapping']['SHARE X']
print(share_x_rule['type'])  # Output: 'indirect'

# Get all direct ad targets
direct_targets = {
    name: info for name, info in rules['classification_rules']['target_mapping'].items()
    if info['type'] == 'direct'
}
```

### Applying Exchange Rates

```python
# Get exchange rate for a period
rate = rules['exchange_rates']['2024-10']  # 1361.0
ad_cost_krw = ad_cost_usd * rate
```

### Calculating Ad Cost Apportionment

```python
# For indirect ads (SHARE X)
formula = rules['apportionment_formula']['formula']
# company_ad_cost = total_ad_cost / total_courses * company_courses

total_ad_cost = 10000000  # 10M KRW
total_courses = rules['course_count']['total_courses']  # 39
company_courses = rules['course_count']['plusx_courses']  # 24

company_ad_cost = total_ad_cost / total_courses * company_courses
```

### Identifying Campaign Targets

```python
import re

campaign_name = "IP_쉐어엑스_산돌_전환"
campaign_patterns = rules['classification_rules']['campaign_patterns']

for pattern_rule in campaign_patterns:
    if re.search(pattern_rule['pattern'], campaign_name):
        target = pattern_rule['default_target']
        print(f"Campaign target: {target}")  # Output: SANDOLL
        break
```

## Classification Rules Summary

### Direct vs. Indirect Ad Costs

| Target | Type | Attribution |
|--------|------|-------------|
| SHARE X | Indirect (간접광고) | Split by course count |
| PLUS X | Direct (직접광고) | 100% to PLUS X |
| BKID | Direct (직접광고) | 100% to BKID |
| BLSN | Direct (직접광고) | 100% to BLSN |
| SANDOLL | Direct (직접광고) | 100% to SANDOLL |

### Apportionment Formula (for Indirect Ad Costs)

```
광고비 = 총 광고비 A ÷ 전체 강의 수 B × 해당 기업 강의 수 C
```

**Translation:**
Ad Cost = Total Ad Cost / Total Course Count × Company Course Count

### Campaign Pattern Recognition

The configuration includes regex patterns for automatic campaign classification:

- **SHARE X Indicator:** Contains `쉐어엑스|Share X|SHARE X|SA_`
- **PLUS X Indicator:** Contains `플러스|PLUS|IP_`
- **BKID Indicator:** Contains `BKID|비케이아이디|DA_`
- **SANDOLL Indicator:** Contains `산돌|SANDOLL`
- **BLSN Indicator:** Contains `블센|BLSN`

## Course Count Reference

- **PLUS X Courses:** 24
- **Union Courses:** 15
- **Total Courses:** 39
- **Note:** Subject to periodic changes (38-40 courses)

## Exchange Rate Reference

The configuration includes exchange rates for 6 periods:

- 2024-10: 1,361.00 KRW/USD
- 2024-11: 1,393.38 KRW/USD
- 2024-12: 1,434.42 KRW/USD
- 2025-01: 1,455.79 KRW/USD
- 2025-02: 1,445.56 KRW/USD
- 2025-03: 1,456.95 KRW/USD

## Data Sources

- **Excel File:** Share X Settlement_Info.xlsx
- **Source Sheet:** 정산서(논리) (Settlement Logic)
- **Supporting Sheet:** 광고비 사용내역 (Ad Cost Usage Details)
- **Extraction Date:** 2026-02-09

## Unique Values Extracted

- **Ad Targets:** 5 (SHARE X, PLUS X, BKID, BLSN, SANDOLL)
- **Media Channels:** 3 (Google, Meta, Naver)
- **Campaign Names:** 21
- **Exchange Rate Periods:** 6

## Validation Checklist

- ✓ JSON is valid and well-formed
- ✓ All classification rules extracted
- ✓ All unique targets identified
- ✓ All unique campaigns identified
- ✓ All channels identified
- ✓ All exchange rates included
- ✓ Apportionment formulas defined
- ✓ Course counts configured
- ✓ Metadata properly recorded
- ✓ UTF-8 encoding verified

## Related Files

- **extract_campaign_rules.py** - Python script used to generate this configuration
- **EXTRACTION_SUMMARY.md** - Detailed extraction process documentation

## Support

For questions about the configuration structure or to update the rules, refer to the extraction script or the Excel source file.

---

**Generated:** 2026-02-09
**Generator:** Claude Code with Python openpyxl
