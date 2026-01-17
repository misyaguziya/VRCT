import os
import shutil

root = os.path.dirname(os.path.dirname(__file__))
shutil.rmtree(os.path.join(root, 'build'), ignore_errors=True)
shutil.rmtree(os.path.join(root, 'dist'), ignore_errors=True)
shutil.rmtree(os.path.join(root, 'src-tauri', 'bin'), ignore_errors=True)
shutil.rmtree(os.path.join(root, 'src-tauri', 'target'), ignore_errors=True)