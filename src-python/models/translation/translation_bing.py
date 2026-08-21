import json
import re


def parse_bing_credentials(host_html: str) -> dict[str, int | str]:
    match = re.search(r"var params_AbusePreventionHelper\s*=\s*(\[.*?\]);", host_html)
    if match is None:
        raise ValueError("Bing credentials were not found")

    values = json.loads(match.group(1))
    if not isinstance(values, list) or len(values) < 2:
        raise ValueError("Bing credentials have an unexpected format")

    return {"key": int(values[0]), "token": str(values[1])}