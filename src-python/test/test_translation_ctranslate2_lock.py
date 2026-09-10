"""CTranslate2 translator/tokenizer のロックに関するテスト (ロードマップ項目 10)。

対象の欠陥:
  Translator.ctranslate2_translator/ctranslate2_tokenizer は mic/speaker の
  _print_transcript スレッドと mainloop ワーカー (チャット送信) から同時に
  呼ばれるシングルトン相当だが、translateCTranslate2()/changeCTranslate2Model()
  はどちらも無ロックだった。tokenizer.src_lang への代入は tokenizer
  インスタンス自体の状態を書き換えるため、mic が "ja" を代入した直後に
  speaker が "en" で上書きすると、mic 側の encode() が英語トークナイザ
  設定で走ってしまう (クラッシュしないので気付きにくい翻訳品質の劣化)。

  修正: Translator に _ctranslate2_lock (RLock) を追加し、
  translateCTranslate2()/changeCTranslate2Model() の全体を保護した。
"""

import threading
import time
import unittest

from models.translation.translation_translator import Translator


class _FakeTokenizer:
    """CTranslate2 tokenizer の代わり。

    src_lang の setter に意図的な遅延を入れることで、「代入」と直後の
    「encode() での読み取り」の間に他スレッドが割り込める窓を広げる
    (実機の tokenizer 呼び出しにも一定の処理時間がかかることを模す)。
    """

    lang_code_to_token: dict = {}

    def __init__(self, set_delay_sec: float = 0.05) -> None:
        self._src_lang = None
        self._set_delay_sec = set_delay_sec
        self.calls: list[tuple] = []  # (encode 時点で見えていた src_lang, message)

    @property
    def src_lang(self):
        return self._src_lang

    @src_lang.setter
    def src_lang(self, value):
        time.sleep(self._set_delay_sec)
        self._src_lang = value

    def encode(self, message):
        self.calls.append((self._src_lang, message))
        return [1, 2, 3]

    def convert_ids_to_tokens(self, ids):
        return ["<tok>"] * len(ids)

    def convert_tokens_to_ids(self, tokens):
        return [1] * len(tokens)

    def decode(self, ids):
        return "decoded"


class _FakeResult:
    def __init__(self, hypotheses):
        self.hypotheses = hypotheses


class _FakeCTranslate2Translator:
    def translate_batch(self, sources, target_prefix):
        return [_FakeResult([["<s>", "tok"]])]


class TranslateCTranslate2LockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.translator = Translator()
        self.tokenizer = _FakeTokenizer()
        self.translator.ctranslate2_tokenizer = self.tokenizer
        self.translator.ctranslate2_translator = _FakeCTranslate2Translator()
        self.translator.is_loaded_ctranslate2_model = True

    def test_concurrent_calls_do_not_observe_each_others_src_lang(self) -> None:
        # mic が "Japanese"、speaker が "English" を同時に翻訳する状況を
        # 再現する。ロックが効いていれば、各呼び出しの encode() 時点で
        # 見える src_lang は必ず「自分が設定した値」のはず。
        barrier = threading.Barrier(2, timeout=5)

        def call(source_language, message):
            barrier.wait()
            self.translator.translateCTranslate2(
                message=message,
                source_language=source_language,
                target_language="jpn_Jpan",
                weight_type="nllb-200-distilled-600M-ct2-int8",
            )

        threads = [
            threading.Thread(target=call, args=("Japanese", "mic-message")),
            threading.Thread(target=call, args=("English", "speaker-message")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(len(self.tokenizer.calls), 2)
        expected = {"mic-message": "Japanese", "speaker-message": "English"}
        for seen_src_lang, message in self.tokenizer.calls:
            self.assertEqual(
                seen_src_lang, expected[message],
                f"{message} の encode() 時点で src_lang が他スレッドに書き換えられていた",
            )

    def test_translate_and_change_model_are_mutually_exclusive(self) -> None:
        # changeCTranslate2Model() が実行中は translateCTranslate2() が
        # 待たされ、破棄途中の tokenizer/translator に触れないことを確認する。
        order = []
        release_change = threading.Event()

        original_from_pretrained = None
        import models.translation.translation_translator as tt_module

        class _SlowTokenizer(_FakeTokenizer):
            pass

        class _FakeAutoTokenizer:
            @staticmethod
            def from_pretrained(*args, **kwargs):
                order.append("change:tokenizer_loading")
                release_change.wait(timeout=5)
                order.append("change:tokenizer_loaded")
                return _SlowTokenizer()

        class _FakeTransformers:
            AutoTokenizer = _FakeAutoTokenizer

        class _FakeCTranslate2Module:
            @staticmethod
            def Translator(*args, **kwargs):
                return _FakeCTranslate2Translator()

        original_ctranslate2 = tt_module.ctranslate2
        original_transformers = tt_module.transformers
        original_weights = tt_module.ctranslate2_weights.get("nllb-200-distilled-600M-ct2-int8")
        tt_module.ctranslate2 = _FakeCTranslate2Module()
        tt_module.transformers = _FakeTransformers()
        tt_module.ctranslate2_weights["nllb-200-distilled-600M-ct2-int8"] = {
            "directory_name": "nllb-200-distilled-600M-ct2-int8",
            "tokenizer": "dummy",
        }

        def run_change():
            self.translator.changeCTranslate2Model(
                path=".", model_type="nllb-200-distilled-600M-ct2-int8",
            )

        def run_translate():
            # change 側が _ctranslate2_lock を確実に取得してから走らせたいので
            # tokenizer_loading が記録されるまで少し待つ。
            while "change:tokenizer_loading" not in order:
                time.sleep(0.01)
            order.append("translate:start")
            self.translator.translateCTranslate2(
                message="hello",
                source_language="Japanese",
                target_language="jpn_Jpan",
                weight_type="nllb-200-distilled-600M-ct2-int8",
            )
            order.append("translate:end")

        # デーモン化 + release_change を必ず set することで、アサーション
        # 失敗時 (= 旧コードで実際に排他されておらず translate 側が
        # from_pretrained の wait より先に完走してしまう場合など) に
        # スレッドが残ってテストプロセスごとハングしないようにする。
        t_change = threading.Thread(target=run_change, daemon=True)
        t_translate = threading.Thread(target=run_translate, daemon=True)

        def _restore():
            tt_module.ctranslate2 = original_ctranslate2
            tt_module.transformers = original_transformers
            if original_weights is not None:
                tt_module.ctranslate2_weights["nllb-200-distilled-600M-ct2-int8"] = original_weights

        # addCleanup は LIFO で実行されるため、実行させたい順序 (release →
        # 各 join → 復元) の逆順で登録する。
        self.addCleanup(_restore)
        self.addCleanup(lambda: t_translate.join(timeout=5))
        self.addCleanup(lambda: t_change.join(timeout=5))
        self.addCleanup(release_change.set)

        t_change.start()
        t_translate.start()

        # translate 側が _ctranslate2_lock 待ちでブロックされている間に
        # change 側を進める。
        time.sleep(0.1)
        self.assertNotIn(
            "translate:end", order,
            "changeCTranslate2Model 実行中に translateCTranslate2 が完了してしまった (排他されていない)",
        )
        release_change.set()

        t_change.join(timeout=5)
        t_translate.join(timeout=5)

        # change の完了 (is_loaded=True) が先に来て、translate はその後で走る。
        self.assertEqual(
            order,
            ["change:tokenizer_loading", "translate:start", "change:tokenizer_loaded", "translate:end"],
        )


if __name__ == "__main__":
    unittest.main()
