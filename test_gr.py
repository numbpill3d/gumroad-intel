import importlib
import os
import unittest
from unittest import mock


os.environ.setdefault("GUMROAD_ACCESS_TOKEN", "test-token")
gr = importlib.import_module("gr")


class PaginationUrlTests(unittest.TestCase):
    def test_rejects_off_domain_url_before_request(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            with self.assertRaisesRegex(ValueError, "non-API URL"):
                gr.get_url("https://example.com/v2/sales?page=2")

        urlopen.assert_not_called()

    def test_rejects_insecure_gumroad_url_before_request(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            with self.assertRaisesRegex(ValueError, "non-API URL"):
                gr.get_url("http://api.gumroad.com/v2/sales?page=2")

        urlopen.assert_not_called()

    def test_accepts_relative_api_url(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"sales": []}'
        with mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
            self.assertEqual(gr.get_url("/v2/sales?page=2"), {"sales": []})

        requested_url = urlopen.call_args.args[0]
        self.assertTrue(requested_url.startswith("https://api.gumroad.com/v2/sales?page=2&"))
        self.assertIn("access_token=test-token", requested_url)


if __name__ == "__main__":
    unittest.main()
