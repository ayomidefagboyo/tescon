#!/usr/bin/env python3
import pandas as pd

df = pd.read_excel('/Users/admin/tescon/backend/EGTL Dump_with_JDE.xlsx', sheet_name='Data')

# Check fallback scenarios
jde_empty = df['Long Text JDE'].isna() | (df['Long Text JDE'] == '')
desc1_available = df['Desc1'].notna() & (df['Desc1'] != '')
desc2_available = df['Desc2'].notna() & (df['Desc2'] != '')

fallback_candidates = jde_empty & (desc1_available | desc2_available)

print(f'Total parts: {len(df):,}')
print(f'Long Text JDE empty: {jde_empty.sum():,}')
print(f'Desc1 available: {desc1_available.sum():,}')
print(f'Desc2 available: {desc2_available.sum():,}')
print(f'Would benefit from fallback: {fallback_candidates.sum():,}')

print('\nSample cases that would use fallback:')
sample_fallback = df[fallback_candidates].head(3)
for i, row in sample_fallback.iterrows():
    print(f'Symbol: {row["Symbol Number"]}')
    print(f'  Long Text JDE: "{row["Long Text JDE"]}"')
    print(f'  Desc1: "{row["Desc1"]}"')
    print(f'  Desc2: "{row["Desc2"]}"')
    desc1 = str(row['Desc1']) if pd.notna(row['Desc1']) else ''
    desc2 = str(row['Desc2']) if pd.notna(row['Desc2']) else ''
    fallback = ' | '.join(filter(None, [desc1, desc2]))
    print(f'  Fallback would be: "{fallback}"')
    print()