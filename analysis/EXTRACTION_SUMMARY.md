# Campaign Classification Rules Extraction Summary

## Execution Status
✓ **SUCCESS** - Campaign rules extracted and saved as JSON

## Files Generated

### 1. **config/campaign_rules.json** (Primary Output)
- **Location**: `/sessions/blissful-festive-dijkstra/mnt/ShareX_Settlement/config/campaign_rules.json`
- **Size**: 3,812 bytes
- **Format**: UTF-8 encoded JSON
- **Validity**: ✓ Valid and well-formed

### 2. **extract_campaign_rules.py** (Python Script)
- **Location**: `/sessions/blissful-festive-dijkstra/mnt/ShareX_Settlement/extract_campaign_rules.py`
- **Purpose**: Reusable script to extract campaign rules from Excel
- **Usage**: `python3 extract_campaign_rules.py`

## Extraction Results

### Ad Targets (Column D)
Total: 5 unique targets

1. **SHARE X** (간접광고 - Indirect Ad Cost)
   - Type: `indirect`
   - Apportionment: Equal by total course count
   - Formula: `company_ad_cost = total_ad_cost / total_courses * company_courses`

2. **PLUS X** (직접광고 - Direct Ad Cost)
   - Type: `direct`
   - Company ID: `plusx`
   - Course Count: 24

3. **BKID** (직접광고 - Direct Ad Cost)
   - Type: `direct`
   - Company ID: `bkid`

4. **BLSN** (직접광고 - Direct Ad Cost)
   - Type: `direct`
   - Company ID: `blsn`

5. **SANDOLL** (직접광고 - Direct Ad Cost)
   - Type: `direct`
   - Company ID: `sandoll`

### Channels (Column C)
Total: 3 unique channels
- Google
- Meta
- Naver

### Campaigns (Column E)
Total: 21 unique campaign names

Key campaign name patterns:
- **SA_쉐어엑스_자상호**: Google Search Ads for Share X
- **IP 프로모션_쉐어엑스**: Promotion for Share X (multiple variations)
- **Instagram - ...**: Meta/Instagram campaigns (10 variations)
- **DA_[쉐어엑스] BKID ...**: Display Ads for BKID
- **2T_쉐어엑스_BKID_...**: Two-tier campaigns for BKID
- **IP_쉐어엑스_**: Multiple IP promotion variants
- **검색 광고**: Search advertising

### Course Count Structure
- **PLUS X Courses**: 24
- **Union Courses**: 15
- **Total Courses**: 39
- **Note**: Subject to periodic changes (38-40 courses)

### Exchange Rates (Column H)
Total: 6 periods

| Period | Exchange Rate (USD to KRW) |
|--------|---------------------------|
| 2024-10 | 1,361.00 |
| 2024-11 | 1,393.38 |
| 2024-12 | 1,434.42 |
| 2025-01 | 1,455.79 |
| 2025-02 | 1,445.56 |
| 2025-03 | 1,456.95 |

## Classification Rules

### Target Mapping
Each ad target is classified according to these rules:

```
SHARE X → Indirect (간접광고)
├─ Description: 통합 광고 - 전체 강의 수로 균등 안분
├─ Apportionment: equal_by_course_count
└─ Formula: company_ad_cost = total_ad_cost / total_courses * company_courses

PLUS X → Direct (직접광고)
├─ Description: 플러스엑스 직접광고비
└─ Attribution: 100% to PLUS X

BKID → Direct (직접광고)
├─ Description: BKID 직접광고비
└─ Attribution: 100% to BKID

BLSN → Direct (직접광고)
├─ Description: 블센 직접광고비
└─ Attribution: 100% to BLSN

SANDOLL → Direct (직접광고)
├─ Description: 산돌 직접광고비
└─ Attribution: 100% to SANDOLL
```

### Campaign Patterns (for classification)
1. **Share X Indicator**: Contains "쉐어엑스|Share X|SHARE X|SA_"
   - Default Target: SHARE X
   - Category: 통합광고

2. **PLUS X Indicator**: Contains "플러스|PLUS|IP_"
   - Default Target: PLUS X
   - Category: 플러스엑스

3. **BKID Indicator**: Contains "BKID|비케이아이디|DA_"
   - Default Target: BKID
   - Category: BKID

4. **SANDOLL Indicator**: Contains "산돌|SANDOLL"
   - Default Target: SANDOLL
   - Category: 산돌

5. **BLSN Indicator**: Contains "블센|BLSN"
   - Default Target: BLSN
   - Category: 블센

## Apportionment Formula

For **indirect ad costs** (SHARE X):
```
광고비 = 총 광고비 A ÷ 전체 강의 수 B × 해당 기업 강의 수 C
```

**English**: Ad Cost = Total Ad Cost / Total Course Count × Company Course Count

For **direct ad costs** (PLUS X, BKID, BLSN, SANDOLL):
```
광고비 = 100% 해당 기업 귀속
```

**English**: Ad Cost = 100% attributed to the specific company

## Source Data

| Aspect | Details |
|--------|---------|
| Source File | Share X Settlement_Info.xlsx |
| Source Sheet | 정산서(논리) (Settlement Logic) |
| Supporting Sheet | 광고비 사용내역 (Ad Cost Usage Details) |
| Data Rows | Row 4 to Row 67 (64 rows of data) |
| Header Row | Row 3 |
| Extraction Date | 2026-02-09 |

## Data Quality Notes

- All unique targets extracted from Column D
- All unique campaign names extracted from Column E
- Exchange rates extracted from Column H (applicable at each row)
- Course counts extracted from Row 1 (K) and Row 2 (L)
- All data properly encoded in UTF-8 for Korean text support
- No data loss or corruption during extraction

## JSON Structure

```json
{
  "classification_rules": {
    "target_mapping": { ... },      // 5 targets
    "campaign_patterns": [ ... ]     // 5 pattern groups
  },
  "channels": [ ... ],               // 3 channels
  "apportionment_formula": { ... },  // Formula details
  "course_count": { ... },           // Course count info
  "exchange_rates": { ... },         // 6 exchange rate periods
  "unique_ad_targets": [ ... ],      // All 5 targets listed
  "unique_campaign_names": [ ... ],  // All 21 campaign names
  "metadata": { ... }                // Extraction metadata
}
```

## Verification Results

- ✓ JSON file is valid and well-formed
- ✓ All unique targets identified: 5
- ✓ All unique campaigns identified: 21
- ✓ All unique channels identified: 3
- ✓ All exchange rates extracted: 6 periods
- ✓ Course counts validated: PLUS X (24) + Union (15) = Total (39)
- ✓ File encoding: UTF-8 (supports Korean characters)

## Next Steps

The generated `campaign_rules.json` file can be used to:

1. **Classify campaigns** automatically based on target and campaign name
2. **Calculate ad cost apportionment** using the provided formula
3. **Apply exchange rates** for the appropriate period
4. **Validate settlement data** against the classification rules
5. **Generate settlement reports** with proper cost attribution

## Usage Example

```python
import json

# Load the rules
with open('config/campaign_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

# Get target type
target = rules['classification_rules']['target_mapping']['SHARE X']
# Output: {'type': 'indirect', 'description': '통합 광고 - 전체 강의 수로 균등 안분', ...}

# Get apportionment formula
formula = rules['apportionment_formula']
# Output: {'description': '광고비 = 총 광고비 A ÷ 전체 강의 수 B × ...', ...}

# Get exchange rate for a period
rate = rules['exchange_rates']['2024-10']
# Output: 1361.0
```

---

**Generated**: 2026-02-09  
**Generator**: Claude Code with Python openpyxl  
**Status**: Complete and Verified
