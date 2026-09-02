# Claude wrote this test suite (2026-09-02)
import json
import logging
from collections import OrderedDict
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import tns_upload_classification as tnsup

FIXTURES = Path(__file__).parent / "fixtures"


def make_response(status_code, json_data=None, json_raises=False):
    resp = MagicMock()
    resp.status_code = status_code
    if json_raises:
        resp.json.side_effect = ValueError("not json")
    else:
        resp.json.return_value = json_data
    return resp


def test_tns_marker_format():
    marker = tnsup._tns_marker(12345, "lvra_bot")
    assert marker == 'tns_marker{"tns_id": "12345", "type": "bot", "name": "lvra_bot"}'


def test_load_json_preserves_order():
    result = tnsup._load_json(FIXTURES / "sample_ordered.json")
    assert isinstance(result, OrderedDict)
    assert list(result.items()) == [("beta", 1), ("alpha", 2), ("gamma", 3)]


def test_load_tns_config_explicit_path():
    config = tnsup.load_tns_config(config_path=str(FIXTURES / "sample_config.yaml"))
    assert config["tns_bot_id"] == "12345"
    assert config["tns_host"] == "sandbox.wis-tns.org"


def test_load_tns_config_env_var(monkeypatch):
    monkeypatch.setenv("mybot_CONFIG_TNS", str(FIXTURES / "sample_config.yaml"))
    config = tnsup.load_tns_config(config_path=None, bot_name="mybot")
    assert config["tns_bot_name"] == "test_bot"


def test_load_tns_config_default_path(monkeypatch):
    monkeypatch.delenv("lvra_CONFIG_TNS", raising=False)
    monkeypatch.setattr(tnsup, "DEFAULT_CONFIG_PATH", str(FIXTURES / "sample_config.yaml"))
    config = tnsup.load_tns_config(config_path=None, bot_name="lvra")
    assert config["tns_api_key"] == "abcdef"


def test_log_status_valid_payload(caplog):
    caplog.set_level(logging.INFO)
    response = make_response(200, {"id_code": 110, "id_message": "OK"})
    tnsup._log_status(response)
    assert "110" in caplog.text
    assert "OK" in caplog.text


@pytest.mark.parametrize(
    "status_code,expected_msg,level",
    [
        (200, "OK", logging.INFO),
        (403, "Forbidden", logging.ERROR),
        (500, "Internal Server Error: Something is broken", logging.ERROR),
        (503, "Service Unavailable", logging.ERROR),
        (404, "Undocumented error", logging.ERROR),
    ],
)
def test_log_status_non_json_response(caplog, status_code, expected_msg, level):
    caplog.set_level(logging.INFO)
    response = make_response(status_code, json_raises=True)
    tnsup._log_status(response)
    assert expected_msg in caplog.text
    assert caplog.records[-1].levelno == level


def test_log_status_missing_keys_falls_back(caplog):
    caplog.set_level(logging.INFO)
    response = make_response(200, {})
    tnsup._log_status(response)
    assert "OK" in caplog.text


def test_upload_files_txt_and_fits(tmp_path, monkeypatch):
    txt_path = tmp_path / "spec.txt"
    txt_path.write_text("wavelength flux\n1 2\n")
    fits_path = tmp_path / "spec.fits"
    fits_path.write_bytes(b"\x00\x01FITSDATA")

    mock_post = MagicMock(
        return_value=make_response(
            200, {"id_code": 200, "id_message": "OK", "data": ["spec.txt", "spec.fits"]}
        )
    )
    monkeypatch.setattr(tnsup.requests, "post", mock_post)

    response = tnsup.upload_files(
        "https://api.example.org", {"User-Agent": "x"}, "key123",
        [str(txt_path), str(fits_path)],
    )

    assert response.status_code == 200
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.example.org/set/file-upload"
    assert kwargs["data"] == {"api_key": "key123"}

    files = kwargs["files"]
    assert set(files.keys()) == {"files[0]", "files[1]"}

    name0, fileobj0, mime0 = files["files[0]"]
    assert name0 == "spec.txt"
    assert mime0 == "text/plain"
    assert fileobj0.read() == "wavelength flux\n1 2\n"

    name1, fileobj1, mime1 = files["files[1]"]
    assert name1 == "spec.fits"
    assert mime1 == "application/fits"
    assert fileobj1.read() == b"\x00\x01FITSDATA"


def test_send_report_posts_parsed_json(tmp_path, monkeypatch):
    report_path = tmp_path / "report.json"
    report_path.write_text('{"b": 1, "a": 2}')

    mock_post = MagicMock(
        return_value=make_response(
            200, {"id_code": 200, "id_message": "OK", "data": {"report_id": "999"}}
        )
    )
    monkeypatch.setattr(tnsup.requests, "post", mock_post)

    response = tnsup.send_report(
        "https://api.example.org", {"User-Agent": "x"}, "key123", str(report_path)
    )

    assert response.status_code == 200
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.example.org/set/bulk-report"
    assert kwargs["data"]["api_key"] == "key123"
    sent = json.loads(kwargs["data"]["data"], object_pairs_hook=OrderedDict)
    assert list(sent.items()) == [("b", 1), ("a", 2)]


def test_get_reply_returns_immediately_on_success(monkeypatch):
    mock_post = MagicMock(return_value=make_response(200, {"data": {"feedback": {}}}))
    monkeypatch.setattr(tnsup.requests, "post", mock_post)
    monkeypatch.setattr(tnsup.time, "sleep", lambda _: None)

    response = tnsup.get_reply("https://api.example.org", {}, "key123", "report_1")

    assert response.status_code == 200
    assert mock_post.call_count == 1


def test_get_reply_retries_until_success(monkeypatch):
    responses = [make_response(404), make_response(404), make_response(200)]
    mock_post = MagicMock(side_effect=responses)
    monkeypatch.setattr(tnsup.requests, "post", mock_post)
    monkeypatch.setattr(tnsup.time, "sleep", lambda _: None)

    response = tnsup.get_reply("https://api.example.org", {}, "key123", "report_1")

    assert response.status_code == 200
    assert mock_post.call_count == 3


def test_get_reply_gives_up_after_timeout(monkeypatch):
    mock_post = MagicMock(return_value=make_response(404))
    monkeypatch.setattr(tnsup.requests, "post", mock_post)
    monkeypatch.setattr(tnsup.time, "sleep", lambda _: None)

    response = tnsup.get_reply("https://api.example.org", {}, "key123", "report_1")

    # elapsed starts at SLEEP_SEC and grows by SLEEP_SEC each retry until it
    # exceeds TIMEOUT: initial call + one retry call per elapsed value <= TIMEOUT.
    expected_calls = 1 + (tnsup.TIMEOUT // tnsup.SLEEP_SEC)
    assert response.status_code == 404
    assert mock_post.call_count == expected_calls
