from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
MAINLOOP = ROOT / 'mainloop.py'
text = MAINLOOP.read_text(encoding='utf-8')
run_mapping = {}
mapping = {}
for mm in re.finditer(r"[\'\"]([^\'\"]+)[\'\"]\s*:\s*[\'\"](/run/[a-zA-Z0-9_\-\\/]+)[\'\"]", text):
    run_mapping[mm.group(1)] = mm.group(2)
for mm in re.finditer(r"[\'\"](/(?:get|set)/[a-zA-Z0-9_\-\\/]+)[\'\"]", text):
    mapping[mm.group(1)] = True
print('run_mapping entries:', len(run_mapping))
print('sample run_mapping keys:', sorted(run_mapping.items())[:10])
print('\nmapping endpoints count:', len(mapping))
# show any endpoints that are exactly '/get/data/'
print('\ncontains /get/data/?', '/get/data/' in mapping)
if '/get/data/' in mapping:
    print('Found /get/data/ literal in mainloop.py text')
# show ones containing '/get/data'
has_get_data = [k for k in mapping.keys() if '/get/data' in k]
print('\nendpoints containing /get/data:', len(has_get_data))
if has_get_data:
    for k in sorted(has_get_data)[:30]:
        print(' -', k)
# print first 20 mapping endpoints
print('\nFirst 40 endpoints:')
for k in sorted(mapping.keys())[:40]:
    print(' -', k)
