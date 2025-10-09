import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAINLOOP = ROOT / 'mainloop.py'
CONTROLLER = ROOT / 'controller.py'
DOC_API = ROOT / 'docs' / 'api.md'
DOC_RUN = ROOT / 'docs' / 'run_events_payloads.md'


def extract_mapping_from_mainloop():
    """
    Import mainloop.py and read 'mapping' and 'run_mapping' objects directly.
    This executes the module in an isolated module object; mainloop has some
    initialization but exposing these dicts is acceptable for verification.
    """
    run_mapping = {}
    mapping = {}
    try:
        spec = importlib.util.spec_from_file_location('project_mainloop', str(MAINLOOP))
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        if loader is None:
            raise RuntimeError('Could not load mainloop module')
        loader.exec_module(module)
        mapping = getattr(module, 'mapping', {}) or {}
        run_mapping = getattr(module, 'run_mapping', {}) or {}
        return mapping, run_mapping
    except Exception as e:
        print('Error importing mainloop.py', e)

    # Fallback: simple regex-based extraction from mainloop.py text
    try:
        text = MAINLOOP.read_text(encoding='utf-8')
        # run_mapping entries like: "transcription_mic": "/run/transcription_send_mic_message",
        for mm in re.finditer(r"[\'\"]([^\'\"]+)[\'\"]\s*:\s*[\'\"](/run/[a-zA-Z0-9_\-\/]+)[\'\"]", text):
            run_mapping[mm.group(1)] = mm.group(2)
        # mapping endpoints: any '/get/...' or '/set/...' literal in file
        for mm in re.finditer(r"[\'\"](/(?:get|set)/[a-zA-Z0-9_\-\/]+)[\'\"]", text):
            mapping[mm.group(1)] = True
    except Exception as e:
        print('Error parsing mainloop.py via fallback', e)

    return mapping, run_mapping


def extract_run_events_from_controller():
    code = CONTROLLER.read_text(encoding='utf-8')
    # find self.run( ... , self.run_mapping["key"], ... ) and direct self.run(..., 
    run_keys = set()
    # pattern for self.run(..., self.run_mapping["xxx"], ...)
    pattern = re.compile(r"self\.run\([^\)]*self\.run_mapping\[\s*[\'\"]([^\'\"]+)[\'\"]\s*\]", re.M)
    for m in pattern.finditer(code):
        run_keys.add(m.group(1))
    # also find self.run(..., "/run/xxx", ...)
    pattern2 = re.compile(r"self\.run\([^\)]*\"(/run/[^\'\"]+)\"", re.M)
    for m in pattern2.finditer(code):
        run_keys.add(m.group(1))
    return run_keys


def extract_endpoints_from_docs():
    api = DOC_API.read_text(encoding='utf-8')
    run = DOC_RUN.read_text(encoding='utf-8') if DOC_RUN.exists() else ''
    endpoints = set()
    run_events = set()
    # conservative extraction: match endpoints that start with /get/ /set/ /run/
    pattern = re.compile(r"(/(?:get|set|run)(?:/[a-zA-Z0-9_\-]+)+)")
    for m in pattern.finditer(api):
        token = m.group(1)
        # drop umbrella placeholders and tokens that end with '/'
        if token in ('/get', '/set', '/run', '/get/data', '/set/data'):
            continue
        if token.endswith('/'):
            continue
        if token.startswith('/run/'):
            run_events.add(token)
        else:
            endpoints.add(token)
    for m in pattern.finditer(run):
        token = m.group(1)
        if token in ('/get', '/set', '/run', '/get/data', '/set/data'):
            continue
        if token.endswith('/'):
            continue
        if token.startswith('/run/'):
            run_events.add(token)
        else:
            endpoints.add(token)
    return endpoints, run_events


def main():
    mapping, run_mapping = extract_mapping_from_mainloop()
    code_endpoints = set(mapping.keys())
    code_run_events = set(run_mapping.values())
    # normalize run events: run_mapping values likely like '/run/…'
    controller_run_keys = extract_run_events_from_controller()

    doc_endpoints, doc_run_events = extract_endpoints_from_docs()

    report = []
    report.append('=== Summary ===')
    report.append(f'Code endpoints (/get,/set,/run): {len(code_endpoints)}')
    report.append(f'Code run_mapping entries: {len(code_run_events)}')
    report.append(f'Controller-run keys found by scan: {len(controller_run_keys)}')
    report.append(f'Documented endpoints found in docs/api.md: {len(doc_endpoints)}')
    report.append(f'Documented run events found in docs: {len(doc_run_events)}')

    # endpoints present in code but not in docs
    missing_in_docs = code_endpoints - doc_endpoints
    extra_in_docs = doc_endpoints - code_endpoints

    report.append('\n=== Endpoints present in code but NOT documented ===')
    if missing_in_docs:
        for e in sorted(missing_in_docs):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    report.append('\n=== Endpoints documented but NOT in code ===')
    if extra_in_docs:
        for e in sorted(extra_in_docs):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    report.append('\n=== Run events present in code (run_mapping) but NOT documented ===')
    missing_run_in_docs = code_run_events - doc_run_events
    if missing_run_in_docs:
        for e in sorted(missing_run_in_docs):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    report.append('\n=== Run keys emitted in controller (self.run mapping keys) but NOT in run_mapping values ===')
    # controller_run_keys are keys like 'connected_network' or '/run/connected_network'
    # normalize controller keys to values: if key starts with '/run/' keep, else map via run_mapping if possible
    normalized = set()
    for k in controller_run_keys:
        if k.startswith('/run/'):
            normalized.add(k)
        else:
            if k in run_mapping:
                normalized.add(run_mapping[k])
            else:
                normalized.add(k)
    # compare normalized with code_run_events
    extra_controller_keys = normalized - code_run_events
    if extra_controller_keys:
        for e in sorted(extra_controller_keys):
            report.append(' - ' + e)
    else:
        report.append(' - None')

    out = '\n'.join(report)
    print(out)

if __name__ == '__main__':
    main()
