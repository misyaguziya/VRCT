import re
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_API = ROOT / 'docs' / 'api.md'
DOC_RUN = ROOT / 'docs' / 'run_events_payloads.md'

# Ensure project root is importable so `import mainloop` works when this script is
# executed from the scripts/ folder.
sys.path.insert(0, str(ROOT))


def main():
    # Delayed imports to avoid module-level import ordering issues (E402 in linters)
    import mainloop
    import controller as controller_module

    mapping_keys = set(mainloop.mapping.keys())
    run_mapping_values = set(mainloop.run_mapping.values())

    # extract controller emitted run keys by source scan
    controller_src = Path(controller_module.__file__).read_text(encoding='utf-8')
    controller_run_keys = set()
    for m in re.finditer(r"self\.run\([^\)]*self\.run_mapping\[\s*[\'\"]([^\'\"]+)[\'\"]\s*\]", controller_src):
        controller_run_keys.add(m.group(1))
    for m in re.finditer(r"self\.run\([^\)]*\"(/run/[a-zA-Z0-9_\-/]+)\"", controller_src):
        controller_run_keys.add(m.group(1))
    # read docs and extract endpoints conservatively (only full endpoints starting with /get/ /set/ /run/)
    api_text = DOC_API.read_text(encoding='utf-8')
    run_text = DOC_RUN.read_text(encoding='utf-8') if DOC_RUN.exists() else ''

    # include delete endpoints as well (e.g. /delete/data/deepl_auth_key)
    endpoint_pattern = re.compile(r"(/(?:get|set|run|delete)[A-Za-z0-9_\-/]*)")

    doc_endpoints = set(m.group(1) for m in endpoint_pattern.finditer(api_text + '\n' + run_text))

    # Remove umbrella placeholder artifacts that sometimes appear due to
    # comma-separated lists or pattern fragments in the markdown. These are
    # not concrete endpoints and should not be treated as documented endpoints
    # for parity checking.
    umbrella_tokens = {
        '/get', '/set', '/run', '/get/data', '/set/data', '/set/enable', '/set/disable'
    }
    # Remove exact umbrella tokens and any accidental entries that end with a
    # trailing slash (these are artifacts of pattern matching in markdown).
    doc_endpoints = {e for e in doc_endpoints if e not in umbrella_tokens and not e.endswith('/')}

    # Compare
    missing_in_docs = mapping_keys - doc_endpoints
    # A documented endpoint is valid if it corresponds to either an incoming mapping (mapping_keys)
    # or an outgoing run event (run_mapping_values). Treat extra_in_docs as anything documented
    # that is neither in mapping_keys nor in run_mapping_values.
    extra_in_docs = doc_endpoints - (mapping_keys | run_mapping_values)

    missing_run_in_docs = run_mapping_values - doc_endpoints

    # Normalize controller keys to run_mapping values
    normalized = set()
    for k in controller_run_keys:
        if k.startswith('/run/'):
            normalized.add(k)
        else:
            if k in mainloop.run_mapping:
                normalized.add(mainloop.run_mapping[k])
            else:
                normalized.add(k)

    extra_controller_keys = normalized - run_mapping_values

    report = []
    report.append('=== Runtime verification report ===')
    report.append(f'Code mapping endpoints: {len(mapping_keys)}')
    report.append(f'Code run_mapping entries: {len(run_mapping_values)}')
    report.append(f'Controller emitted run keys: {len(controller_run_keys)}')
    report.append(f'Documented endpoints (docs): {len(doc_endpoints)}')

    report.append('\n--- Endpoints present in code but NOT documented ---')
    if missing_in_docs:
        for e in sorted(missing_in_docs):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    report.append('\n--- Endpoints documented but NOT in code ---')
    if extra_in_docs:
        for e in sorted(extra_in_docs):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    report.append('\n--- Run events present in code (run_mapping) but NOT documented ---')
    if missing_run_in_docs:
        for e in sorted(missing_run_in_docs):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    report.append('\n--- Run keys emitted in controller (normalized) but NOT in run_mapping values ---')
    if extra_controller_keys:
        for e in sorted(extra_controller_keys):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    print('\n'.join(report))

    # Also output JSON for downstream processing
    out = {
        'mapping_keys': sorted(mapping_keys),
        'run_mapping_values': sorted(run_mapping_values),
        'controller_run_keys': sorted(controller_run_keys),
        'doc_endpoints': sorted(doc_endpoints),
        'missing_in_docs': sorted(missing_in_docs),
        'extra_in_docs': sorted(extra_in_docs),
        'missing_run_in_docs': sorted(missing_run_in_docs),
        'extra_controller_keys': sorted(extra_controller_keys),
    }
    print('\nJSON_OUTPUT_START')
    print(json.dumps(out))
    print('JSON_OUTPUT_END')


if __name__ == '__main__':
    main()
