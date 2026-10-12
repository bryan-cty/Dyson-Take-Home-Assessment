"""Build the offline dashboard from the three prepared CSVs. No notebook execution."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs'
source_paths = [OUTPUT / name for name in ['sessions.csv', 'battery_changes.csv', 'motor_changes.csv']]
source_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths]
sessions = pd.read_csv(source_paths[0])
battery = pd.read_csv(source_paths[1])
motor = pd.read_csv(source_paths[2])
groups = ['Normal', 'Return/Repair']
session_key = ['group', 'anonymized_serial', 'session_id']
battery_key = ['group', 'anonymized_serial', 'battery_id', 'hdr_timestamp']
motor_key = ['group', 'anonymized_serial', 'hdr_timestamp']
battery_columns = ['change_1', 'change_2', 'change_3']
motor_columns = [
    'change_power_lt_50_seconds', 'change_power_50_75_seconds',
    'change_power_75_100_seconds', 'change_power_100_125_seconds',
    'change_power_125_150_seconds', 'change_power_150_200_seconds',
    'change_power_200_300_seconds', 'change_power_300_400_seconds',
    'change_power_400_500_seconds', 'change_power_500_600_seconds',
    'change_power_600_700_seconds', 'change_power_700_800_seconds',
    'change_power_800_900_seconds', 'change_power_gt_900_seconds'
]
fault_columns = ['blockage', 'filter_wash', 'hot_battery']

# Fail before writing a dashboard if prepared records no longer meet the rules.
for table, keys in [(sessions, session_key), (battery, battery_key), (motor, motor_key)]:
    assert not table[keys].isna().any().any(), 'Missing record keys'
    assert not table.duplicated(keys).any(), 'Repeated record keys'
    assert set(table['group']) == set(groups), 'Unexpected or missing group'
for table, columns in [(battery, battery_columns), (motor, motor_columns)]:
    assert not table[columns].isna().any().any(), 'Missing usage increases'
    assert np.isfinite(table[columns].to_numpy()).all(), 'Non-finite usage increases'
    assert not (table[columns] < 0).any().any(), 'Negative usage increases'
    assert (table['time_gap'] > 0).all(), 'Invalid interval length'
    assert np.allclose(table[columns].sum(axis=1), table['total_change']), 'Change total mismatch'
    assert (table['total_change'] <= table['time_gap']).all(), 'Usage exceeds interval length'
assert sessions[fault_columns].isin([0, 1]).all().all(), 'Fault flags must be 0 or 1'
assert sessions['duration_eligible'].isin([True, False]).all(), 'Missing eligibility flag'
expected_eligible = sessions['clean_duration'].gt(0) & sessions['clean_duration'].le(3600)
assert sessions['duration_eligible'].eq(expected_eligible).all(), 'Duration eligibility changed'

# Only these aggregates are embedded in the delivered HTML.
payload = {
    'groups': groups,
    'durationLabels': ['Under 1 min', '1–5 min', '5–10 min', '10–60 min'],
    'faultLabels': ['Blockage', 'Filter wash', 'Hot battery'],
    'batteryLabels': ['Power 1', 'Power 2', 'Power 3'],
    'motorLabels': ['<50', '50–75', '75–100', '100–125', '125–150', '150–200',
                    '200–300', '300–400', '400–500', '500–600', '600–700',
                    '700–800', '800–900', '>900'],
    'byGroup': {}
}
for group in groups:
    group_sessions = sessions.loc[sessions['group'] == group]
    eligible = group_sessions.loc[group_sessions['duration_eligible']]
    group_battery = battery.loc[battery['group'] == group]
    group_motor = motor.loc[motor['group'] == group]
    duration_bands = pd.cut(eligible['clean_duration'], [0, 60, 300, 600, 3601], right=False)
    duration_counts = duration_bands.value_counts(sort=False)
    battery_seconds = group_battery[battery_columns].sum()
    motor_seconds = group_motor[motor_columns].sum()
    assert len(eligible) > 0 and battery_seconds.sum() > 0 and motor_seconds.sum() > 0
    assert duration_counts.sum() == len(eligible)
    payload['byGroup'][group] = {
        'sessions': len(group_sessions),
        'sessionMachines': int(group_sessions['anonymized_serial'].nunique()),
        'durationSessions': len(eligible),
        'durationCounts': duration_counts.astype(int).tolist(),
        'faultCounts': group_sessions[fault_columns].sum().astype(int).tolist(),
        'batteryIntervals': len(group_battery),
        'batteryMachines': int(group_battery['anonymized_serial'].nunique()),
        'batterySeconds': battery_seconds.tolist(),
        'motorIntervals': len(group_motor),
        'motorMachines': int(group_motor['anonymized_serial'].nunique()),
        'motorSeconds': motor_seconds.tolist()
    }

# Acceptance figures from the submitted report, rounded to two decimal places.
expected = {'Normal': [12.90, 1.43, 2.51, 9.26], 'Return/Repair': [16.27, 3.72, 18.87, 16.04]}
for group in groups:
    d = payload['byGroup'][group]
    actual = [100*d['durationCounts'][3]/d['durationSessions'],
              100*d['faultCounts'][0]/d['sessions'],
              100*d['batterySeconds'][2]/sum(d['batterySeconds']),
              100*d['motorSeconds'][7]/sum(d['motorSeconds'])]
    assert [round(value, 2) for value in actual] == expected[group], 'Report figures changed'
assert len(sessions) == 32391 and sessions['duration_eligible'].sum() == 30419
assert len(battery) == 869 and len(motor) == 842
assert battery.groupby('group')['anonymized_serial'].nunique().to_dict() == {'Normal': 25, 'Return/Repair': 37}
assert motor.groupby('group')['anonymized_serial'].nunique().to_dict() == {'Normal': 54, 'Return/Repair': 37}

serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace('</', r'<\/')
template = (ROOT / 'dashboard/template.html').read_text(encoding='utf-8-sig')
html = template.replace('__PLOTLY__', get_plotlyjs()).replace('__DATA__', serialized)
assert 'anonymized_serial' not in serialized and 'battery_id' not in serialized
assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths] == source_hashes
(OUTPUT / 'telemetry_dashboard.html').write_text(html, encoding='utf-8')
print('Built outputs/telemetry_dashboard.html with aggregate data only.')
print('Verified: report percentages, 32,391 sessions, 30,419 eligible durations, 869 battery intervals, 842 motor intervals.')
print('Verified: record keys, missing values, non-negative increases, elapsed-time bounds and unchanged source CSVs.')
