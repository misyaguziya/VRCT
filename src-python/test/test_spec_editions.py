"""spec/backend.spec が エディションごとに正しい venv を参照することを保証する。

もともと backend.spec と backend_cuda.spec の2本に分かれていて、差分は venv
パスと hiddenimports だけだった。そして**実際にドリフトしていた**:
backend_cuda.spec が hf_xet だけ `.venv` (CPU 側) を指しており、CUDA 版の
ビルドが `.venv` の存在に依存していた。誰も検査していなかったので気付かれずに
残っていた (AMD 対応 PR-3 で1本化するときに発見)。

同じ事故を機械的に止めるためのガードテスト。振る舞いのテストではない。
PyInstaller は動かさず、spec を Python として exec して Analysis に渡る引数だけ
を見る。エディションを増やすとき (PR-5 の AMD) にここも増やすこと。
"""
from pathlib import Path
import os
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "spec" / "backend.spec"

# エディションと、その edition で参照されるべき venv ディレクトリ名。
_EXPECTED_VENV = {
    "cpu": ".venv",
    "cuda": ".venv_cuda",
}

# CUDA 版だけが必要とする hiddenimports。ctranslate2 が GPU 実行時に
# LoadLibrary で遅延ロードするDLLの提供元で、依存解析には掛からない。
_CUDA_ONLY_HIDDENIMPORTS = ("nvidia.cublas", "nvidia.cudnn")


class _Stub:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _Stub()


def _captureAnalysis(edition):
    """spec を exec して Analysis に渡る kwargs を返す。

    edition が None のときは環境変数を消して既定の挙動を見る。
    """
    captured = {}

    def Analysis(scripts, **kwargs):
        captured.update(kwargs)
        captured["scripts"] = scripts
        return _Stub()

    original = os.environ.get("VRCT_BUILD_EDITION")
    if edition is None:
        os.environ.pop("VRCT_BUILD_EDITION", None)
    else:
        os.environ["VRCT_BUILD_EDITION"] = edition
    namespace = {
        "Analysis": Analysis, "PYZ": _Stub, "EXE": _Stub, "COLLECT": _Stub,
        "__file__": str(SPEC_PATH),
    }
    try:
        exec(compile(SPEC_PATH.read_text(encoding="utf-8"), str(SPEC_PATH), "exec"),
             namespace)
    finally:
        if original is None:
            os.environ.pop("VRCT_BUILD_EDITION", None)
        else:
            os.environ["VRCT_BUILD_EDITION"] = original
    return captured


def _venvsReferencedBy(datas):
    """datas のうち venv 配下を指すエントリから、venv 名の集合を作る。"""
    venvs = set()
    for source, _dest in datas:
        parts = Path(str(source)).parts
        for part in parts:
            if part.startswith(".venv"):
                venvs.add(part)
    return venvs


class SpecEditionTests(unittest.TestCase):
    def test_spec_file_exists(self):
        self.assertTrue(SPEC_PATH.is_file(), f"{SPEC_PATH} が無い")

    def test_every_edition_uses_exactly_one_venv(self):
        """これがドリフトを止める本体。

        1つの edition の datas が2つ以上の venv を混ぜて参照していたら、
        それがまさに以前起きていた事故。
        """
        for edition, expected in _EXPECTED_VENV.items():
            with self.subTest(edition=edition):
                datas = _captureAnalysis(edition)["datas"]
                self.assertEqual(
                    _venvsReferencedBy(datas), {expected},
                    f"edition={edition} の datas が参照する venv が {expected} だけになっていない",
                )

    def test_default_edition_is_cpu(self):
        """環境変数なしで `pyinstaller spec/backend.spec` を叩いたときに
        従来と同じ CPU 版が出ること。"""
        datas = _captureAnalysis(None)["datas"]
        self.assertEqual(_venvsReferencedBy(datas), {".venv"})

    def test_cuda_edition_declares_the_lazily_loaded_nvidia_packages(self):
        hiddenimports = _captureAnalysis("cuda")["hiddenimports"]
        for name in _CUDA_ONLY_HIDDENIMPORTS:
            self.assertIn(name, hiddenimports)

    def test_cpu_edition_does_not_declare_nvidia_packages(self):
        """CPU 版に nvidia.* を入れると、無い物を探して収集が失敗する。"""
        hiddenimports = _captureAnalysis("cpu")["hiddenimports"]
        for name in _CUDA_ONLY_HIDDENIMPORTS:
            self.assertNotIn(name, hiddenimports)

    def test_editions_share_everything_except_venv_and_hiddenimports(self):
        """エディション間の差分が venv と hiddenimports だけであること。

        ここが増えていたら、1本にまとめた前提が崩れている。
        """
        cpu = _captureAnalysis("cpu")
        cuda = _captureAnalysis("cuda")
        for key in ("scripts", "excludes", "binaries", "hookspath",
                    "runtime_hooks", "noarchive", "optimize"):
            with self.subTest(key=key):
                self.assertEqual(cpu.get(key), cuda.get(key))
        # datas のうち venv 配下でないものは共通。
        def non_venv(datas):
            return sorted(
                (str(s), str(d)) for s, d in datas
                if not any(p.startswith(".venv") for p in Path(str(s)).parts)
            )
        self.assertEqual(non_venv(cpu["datas"]), non_venv(cuda["datas"]))

    def test_unknown_edition_is_rejected(self):
        """タイポで黙って CPU 版が出るより、止まった方が良い。"""
        with self.assertRaises(SystemExit):
            _captureAnalysis("gpu")  # インストーラ側の語彙 ("gpu") との混同

    def test_build_scripts_pass_a_known_edition(self):
        """bat/build*.bat が設定する edition が spec 側の表と一致すること。

        片方だけ直して不一致になると、ビルドが素の SystemExit で落ちる。
        """
        for script, expected in (("build.bat", "cpu"), ("build_cuda.bat", "cuda")):
            with self.subTest(script=script):
                text = (REPO_ROOT / "bat" / script).read_text(encoding="utf-8")
                self.assertIn(f"set VRCT_BUILD_EDITION={expected}", text)
                self.assertIn("spec/backend.spec", text)


if __name__ == "__main__":
    unittest.main()
