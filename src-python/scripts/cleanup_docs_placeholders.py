from pathlib import Path
p=Path(__file__).resolve().parents[1]/'docs'/'api.md'
text=p.read_text(encoding='utf-8')
lines=[]
for line in text.splitlines():
    stripped=line.strip()
    # Remove exact umbrella placeholder tokens or standalone list entries
    if stripped in ('- /set/enable', '- /set/disable', '- /get/data/', '/set/enable', '/set/disable', '/get/data/'):
        continue
    # Remove lines that are just '/get/data' or '/set/data' or '/run/' etc
    if stripped in ('/get/data', '/set/data', '/run/', '/get', '/set', '/run'):
        continue
    lines.append(line)
new='\n'.join(lines)
p.write_text(new,encoding='utf-8')
print('cleaned')
