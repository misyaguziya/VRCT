import subprocess

# VRCT-sidecar.exe を強制終了
try:
    subprocess.run(
        ["taskkill", "/IM", "VRCT-sidecar.exe", "/F"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
except Exception:
    pass