"""pytest collection configuration for src-python.

collect_ignore excludes files that match pytest's test_*.py discovery glob
by naming coincidence but are not pytest suites: standalone, manually-run
CLI diagnostic tools that talk to a real backend process/instance (see
docs/test_endpoints.md and docs/test_client.md). Both unconditionally
delete config.json in the current working directory on import, and
test_endpoints.py additionally imports mainloop's real main_instance --
merely collecting them (even though pytest cannot actually run their
__init__-having "test" classes) is enough to trigger those side effects
against whatever real config.json happens to be in the working directory.

Neither file is meant to run under pytest; both are still fully usable
the documented way (`python test_endpoints.py`, `python test_client.py`).
"""

collect_ignore = [
    "test_endpoints.py",
    "test_client.py",
]
