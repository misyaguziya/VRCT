import unittest

from models.translation.translation_bing import parse_bing_credentials


class TestBingClient(unittest.TestCase):
    HOST_HTML = """
        <div id="tta_outGDCont" data-iid="translator.5028"></div>
        <script>
            var params_AbusePreventionHelper = [123456, "token-value", 3600000];
            var config = {IG:"ig-value"};
        </script>
    """

    def test_parse_credentials_without_executing_javascript(self) -> None:
        self.assertEqual(
            parse_bing_credentials(self.HOST_HTML),
            {"key": 123456, "token": "token-value"},
        )

    def test_rejects_missing_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "credentials were not found"):
            parse_bing_credentials("<html></html>")


if __name__ == "__main__":
    unittest.main()