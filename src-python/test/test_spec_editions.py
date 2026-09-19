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
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "spec" / "backend.spec"

# エディションと、その edition で参照されるべき venv ディレクトリ名。
_EXPECTED_VENV = {
    "cpu": ".venv",
    "cuda": ".venv_cuda",
    "amd": ".venv_amd",
}

# AMD 版は HIP SDK から ROCm ランタイムを集めるので HIP_PATH が要る。
# CI やこの開発機には SDK が無いため、datas を見るテストでは偽の SDK を作る。
_AMD_FAKE_SDK_FILES = (
    "bin/amdhip64_7.dll",
    "bin/amd_comgr_3.dll",
    "bin/hipblas.dll",
    "bin/hipblaslt.dll",
    "bin/rocblas.dll",
    # Tensile カーネル。同梱対象の gfx と、対象外の gfx を両方置いて
    # 絞り込みが効いているかを見る。
    "bin/rocblas/library/TensileLibrary_foo_gfx1100.dat",
    "bin/rocblas/library/TensileLibrary_foo_gfx1201.dat",
    "bin/rocblas/library/TensileLibrary_foo_gfx906.dat",
    "bin/rocblas/library/TensileLibrary_foo_gfx1030.dat",
    "bin/rocblas/library/TensileManifest.txt",  # gfx を含まない共通ファイル
)

# CUDA 版だけが必要とする hiddenimports。ctranslate2 が GPU 実行時に
# LoadLibrary で遅延ロードするDLLの提供元で、依存解析には掛からない。
_CUDA_ONLY_HIDDENIMPORTS = ("nvidia.cublas", "nvidia.cudnn")


class _Stub:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _Stub()


def _captureAnalysis(edition, hip_path=None):
    """spec を exec して Analysis に渡る kwargs を返す。

    edition が None のときは環境変数を消して既定の挙動を見る。
    hip_path を渡すと HIP_PATH を差し替える (AMD 版の datas 検査用)。
    """
    captured = {}

    def Analysis(scripts, **kwargs):
        captured.update(kwargs)
        captured["scripts"] = scripts
        return _Stub()

    originals = {k: os.environ.get(k) for k in ("VRCT_BUILD_EDITION", "HIP_PATH")}
    if edition is None:
        os.environ.pop("VRCT_BUILD_EDITION", None)
    else:
        os.environ["VRCT_BUILD_EDITION"] = edition
    if hip_path is None:
        os.environ.pop("HIP_PATH", None)
    else:
        os.environ["HIP_PATH"] = str(hip_path)
    namespace = {
        "Analysis": Analysis, "PYZ": _Stub, "EXE": _Stub, "COLLECT": _Stub,
        "__file__": str(SPEC_PATH),
    }
    try:
        exec(compile(SPEC_PATH.read_text(encoding="utf-8"), str(SPEC_PATH), "exec"),
             namespace)
    finally:
        for key, value in originals.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    # spec 側のモジュール変数 (_AMD_GFX_TARGETS 等) を見たいテストのために
    # 名前空間も返す。ソースを途中で切って exec すると、後方で定義されている
    # 変数が取れない (実際にそれで KeyError を踏んだ)。
    captured["__spec_globals__"] = namespace
    return captured


def _makeFakeHipSdk(root: Path) -> Path:
    for relative in _AMD_FAKE_SDK_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake")
    return root


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

    def setUp(self):
        # AMD 版は HIP SDK から ROCm ランタイムを集めるので HIP_PATH が要る。
        # 実 SDK は無いので偽物を作る (datas の組み立てだけを検査する)。
        self._sdk_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._sdk_tmp.cleanup)
        self.fake_sdk = _makeFakeHipSdk(Path(self._sdk_tmp.name))

    def _capture(self, edition):
        """edition に応じて必要な環境を与えて spec を評価する。"""
        return _captureAnalysis(
            edition, hip_path=self.fake_sdk if edition == "amd" else None)

    def test_every_edition_uses_exactly_one_venv(self):
        """これがドリフトを止める本体。

        1つの edition の datas が2つ以上の venv を混ぜて参照していたら、
        それがまさに以前起きていた事故。
        """
        for edition, expected in _EXPECTED_VENV.items():
            with self.subTest(edition=edition):
                datas = self._capture(edition)["datas"]
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
        for script, expected in (("build.bat", "cpu"),
                                 ("build_cuda.bat", "cuda"),
                                 ("build_amd.bat", "amd")):
            with self.subTest(script=script):
                text = (REPO_ROOT / "bat" / script).read_text(encoding="utf-8")
                self.assertIn(f"set VRCT_BUILD_EDITION={expected}", text)
                self.assertIn("spec/backend.spec", text)


class AmdRuntimeBundlingTests(unittest.TestCase):
    """AMD 版が ROCm ランタイムを同梱する部分 (PR-5)。

    実 SDK が無いので偽の SDK ツリーを作り、datas の組み立てだけを検査する。
    実際にロードできるかは実機検証 (tools/amd_spike) の担当。
    """

    def setUp(self):
        self._sdk_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._sdk_tmp.cleanup)
        self.fake_sdk = _makeFakeHipSdk(Path(self._sdk_tmp.name))

    def _amdDatas(self):
        return _captureAnalysis("amd", hip_path=self.fake_sdk)["datas"]

    def test_requires_hip_path(self):
        """HIP_PATH 無しで amd をビルドしようとしたら、読める理由で止まること。

        黙って ROCm ランタイム無しの配布物が出ると、実行時に初めて壊れる。
        """
        with self.assertRaises(SystemExit) as caught:
            _captureAnalysis("amd", hip_path=None)
        self.assertIn("HIP_PATH", str(caught.exception))

    def test_rejects_a_hip_path_without_bin(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(SystemExit):
                _captureAnalysis("amd", hip_path=Path(empty))

    def test_bundles_the_rocm_runtime_dlls_at_the_bundle_root(self):
        datas = self._amdDatas()
        bundled = {Path(str(src)).name: str(dest) for src, dest in datas}
        for name in ("amdhip64_7.dll", "amd_comgr_3.dll", "hipblas.dll",
                     "hipblaslt.dll", "rocblas.dll"):
            with self.subTest(dll=name):
                self.assertIn(name, bundled)
                self.assertEqual(bundled[name], ".")

    def test_bundles_only_the_supported_gfx_kernels(self):
        datas = self._amdDatas()
        kernels = [Path(str(src)).name for src, dest in datas
                   if "library" in str(dest)]
        self.assertIn("TensileLibrary_foo_gfx1100.dat", kernels)
        self.assertIn("TensileLibrary_foo_gfx1201.dat", kernels)
        # 同梱していない世代は落とす (容量削減。900MB -> 300MB 程度)。
        self.assertNotIn("TensileLibrary_foo_gfx906.dat", kernels)
        self.assertNotIn("TensileLibrary_foo_gfx1030.dat", kernels)
        # gfx 名を含まない共通ファイルは落とすと動かないので残す。
        self.assertIn("TensileManifest.txt", kernels)

    def test_tensile_kernels_keep_their_path_relative_to_rocblas(self):
        """rocblas.dll は自分の隣の rocblas/library から Tensile を探す。"""
        datas = self._amdDatas()
        kernel_dests = {str(dest) for src, dest in datas
                        if "Tensile" in Path(str(src)).name}
        self.assertEqual(kernel_dests, {os.path.join("rocblas", "library")})

    def test_amd_does_not_declare_the_nvidia_packages(self):
        hiddenimports = _captureAnalysis("amd", hip_path=self.fake_sdk)["hiddenimports"]
        for name in _CUDA_ONLY_HIDDENIMPORTS:
            self.assertNotIn(name, hiddenimports)

    def test_cpu_and_cuda_editions_never_touch_the_hip_sdk(self):
        """AMD 分岐が CPU/CUDA 版に混ざっていないこと。

        HIP_PATH が設定された開発機で CPU 版をビルドしても、ROCm の DLL が
        紛れ込まないようにする。
        """
        for edition in ("cpu", "cuda"):
            with self.subTest(edition=edition):
                datas = _captureAnalysis(edition, hip_path=self.fake_sdk)["datas"]
                sources = " ".join(str(src) for src, _dest in datas)
                self.assertNotIn(str(self.fake_sdk), sources)

    def test_bundled_gfx_targets_match_the_runtime_arch_gate(self):
        """spec が同梱する gfx 世代と、utils が一覧に出す世代が一致すること。

        食い違うと「選べるのに必ずモデル読み込みで失敗する」デバイスが出る。
        spec と utils.py で同じ情報を別の粒度で持っているので、ここで縛る。
        """
        import utils

        # edition=cpu で評価しても _AMD_GFX_TARGETS はモジュール変数なので取れる
        # (HIP SDK も要らない)。
        spec_globals = _captureAnalysis("cpu")["__spec_globals__"]
        # gfx1100 -> 11 のように、gfx 名の先頭2桁を major として取り出す。
        majors = {int(target[3:5]) for target in spec_globals["_AMD_GFX_TARGETS"]}
        self.assertEqual(majors, set(utils._AMD_SUPPORTED_ARCH_MAJORS))


if __name__ == "__main__":
    unittest.main()
