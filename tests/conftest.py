from __future__ import annotations

import contextlib
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from comictagger_jp_talker.sources import ndl
from comictagger_jp_talker.talker import JapaneseBooksTalker


@pytest.fixture(autouse=True)
def offline(request, monkeypatch):
    if request.node.get_closest_marker("network") and os.getenv("JPBOOKS_RUN_NETWORK_TESTS") == "1":
        return

    def forbidden(*args, **kwargs):
        raise AssertionError("Unit tests must not access the network")

    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    monkeypatch.setattr(ndl._LIMITER, "ratelimit", lambda *args, **kwargs: contextlib.nullcontext())


@pytest.fixture
def xml_bytes():
    return (Path(__file__).parent / "fixtures" / "ndl.xml").read_bytes()


@pytest.fixture
def record(xml_bytes):
    return ndl.parse_sru(xml_bytes).records[0]


@pytest.fixture
def source(tmp_path, monkeypatch, xml_bytes):
    source = ndl.NDLSource(tmp_path)
    response = requests.Response()
    response.status_code = 200
    response._content = xml_bytes
    monkeypatch.setattr(source.session, "get", Mock(return_value=response))
    yield source
    source.session.close()
    source.cache.close()


@pytest.fixture
def talker(tmp_path, source):
    talker = JapaneseBooksTalker("1.6.0b9", tmp_path)
    talker._source = source
    return talker
