import os

import pytest


from llm.client import LLMClient, LLMConfig


def test_dummy_status():

    client = LLMClient(LLMConfig(provider="dummy"))

    status = client.status()

    assert status["provider"] == "dummy"

    assert status["ok"] is False


def test_openai_placeholder_key():

    old = os.environ.get("OPENAI_API_KEY")

    os.environ["OPENAI_API_KEY"] = "..."

    try:

        with pytest.raises(RuntimeError):

            LLMClient(LLMConfig(provider="openai"))

    finally:

        if old is None:

            os.environ.pop("OPENAI_API_KEY", None)

        else:

            os.environ["OPENAI_API_KEY"] = old


def test_trim_history():

    client = LLMClient(LLMConfig(provider="dummy", history_max_messages=3))

    client.history = [
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "5"},
    ]

    client._trim_history()

    assert len(client.history) == 3

    assert client.history[0]["content"] == "3"
