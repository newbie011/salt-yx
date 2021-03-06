from urllib.parse import urlencode

import salt.utils.json
import salt.utils.yaml
from tests.support.cherrypy_testclasses import BaseToolsTest


class TestOutFormats(BaseToolsTest):
    def __get_cp_config__(self):
        return {
            "tools.hypermedia_out.on": True,
        }

    def test_default_accept(self):
        request, response = self.request("/")
        self.assertEqual(response.headers["Content-type"], "application/json")

    def test_unsupported_accept(self):
        request, response = self.request(
            "/", headers=(("Accept", "application/ms-word"),)
        )
        self.assertEqual(response.status, "406 Not Acceptable")

    def test_json_out(self):
        request, response = self.request("/", headers=(("Accept", "application/json"),))
        self.assertEqual(response.headers["Content-type"], "application/json")

    def test_yaml_out(self):
        request, response = self.request(
            "/", headers=(("Accept", "application/x-yaml"),)
        )
        self.assertEqual(response.headers["Content-type"], "application/x-yaml")


class TestInFormats(BaseToolsTest):
    def __get_cp_config__(self):
        return {
            "tools.hypermedia_in.on": True,
        }

    def test_urlencoded_ctype(self):
        data = {"valid": "stuff"}
        raw = "valid=stuff"
        request, response = self.request(
            "/",
            method="POST",
            body=urlencode(data),
            headers=(("Content-type", "application/x-www-form-urlencoded"),),
        )
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(request.raw_body, raw)
        self.assertDictEqual(request.unserialized_data, data)

    def test_urlencoded_multi_args(self):
        multi_args = "arg=arg1&arg=arg2"
        expected = {"arg": ["arg1", "arg2"]}
        request, response = self.request(
            "/",
            method="POST",
            body=multi_args,
            headers=(("Content-type", "application/x-www-form-urlencoded"),),
        )
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(request.raw_body, multi_args)
        self.assertDictEqual(request.unserialized_data, expected)

    def test_json_ctype(self):
        data = {"valid": "stuff"}
        request, response = self.request(
            "/",
            method="POST",
            body=salt.utils.json.dumps(data),
            headers=(("Content-type", "application/json"),),
        )
        self.assertEqual(response.status, "200 OK")
        self.assertDictEqual(request.unserialized_data, data)

    def test_json_as_text_out(self):
        """
        Some service send JSON as text/plain for compatibility purposes
        """
        data = {"valid": "stuff"}
        request, response = self.request(
            "/",
            method="POST",
            body=salt.utils.json.dumps(data),
            headers=(("Content-type", "text/plain"),),
        )
        self.assertEqual(response.status, "200 OK")
        self.assertDictEqual(request.unserialized_data, data)

    def test_yaml_ctype(self):
        data = {"valid": "stuff"}
        request, response = self.request(
            "/",
            method="POST",
            body=salt.utils.yaml.safe_dump(data),
            headers=(("Content-type", "application/x-yaml"),),
        )
        self.assertEqual(response.status, "200 OK")
        self.assertDictEqual(request.unserialized_data, data)


class TestCors(BaseToolsTest):
    def __get_cp_config__(self):
        return {
            "tools.cors_tool.on": True,
        }

    def test_option_request(self):
        request, response = self.request(
            "/", method="OPTIONS", headers=(("Origin", "https://domain.com"),)
        )
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"), "https://domain.com"
        )
