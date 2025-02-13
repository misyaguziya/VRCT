import shutil

shutil.rmtree('build', ignore_errors=True)
shutil.rmtree('dist', ignore_errors=True)
shutil.rmtree('src-tauri\\bin', ignore_errors=True)
shutil.rmtree('src-tauri\\target', ignore_errors=True)