import pytest

from purchase_office.llm import FakeLLMClient, LLMClient, parse_json_object
from purchase_office.roles.base import Role
from purchase_office.config import Clearance


def test_llm_client_is_a_protocol():
    # LLMClient is a protocol; FakeLLMClient satisfies it structurally.
    client = FakeLLMClient(scripted={"decision": "approve", "note": "ok"})
    assert isinstance(client, LLMClient)


def test_fake_llm_returns_scripted_dict():
    client = FakeLLMClient(scripted={"decision": "approve", "note": "ok"})
    result = client.complete(prompt="anything", schema={"type": "object"})
    assert result == {"decision": "approve", "note": "ok"}


def test_fake_llm_sequences_multiple_responses():
    client = FakeLLMClient(
        scripted=[
            {"decision": "approve", "note": "first"},
            {"decision": "reject", "note": "second"},
        ]
    )
    assert client.complete("p", {}) == {"decision": "approve", "note": "first"}
    assert client.complete("p", {}) == {"decision": "reject", "note": "second"}


def test_parse_json_object_takes_bare_json():
    assert parse_json_object('{"decision": "approve", "note": "ok"}') == {
        "decision": "approve",
        "note": "ok",
    }


def test_parse_json_object_takes_fenced_json():
    text = 'Here is my verdict:\n```json\n{"decision": "reject", "note": "no"}\n```'
    assert parse_json_object(text) == {"decision": "reject", "note": "no"}


def test_parse_json_object_takes_json_in_prose():
    text = 'The vendor looks fine. {"decision": "approve", "note": "ok"} Thank you.'
    assert parse_json_object(text) == {"decision": "approve", "note": "ok"}


def test_parse_json_object_raises_on_garbage():
    with pytest.raises(ValueError):
        parse_json_object("I approve this purchase wholeheartedly.")


def test_role_prompt_demands_a_json_verdict():
    role = Role(
        name="legal",
        identity="key",
        clearance=Clearance(tools=[], read=[]),
        tools={},
        llm=None,
    )
    prompt = role.build_prompt({"request": "5 x widget"})
    assert '"decision"' in prompt
    assert "approve" in prompt and "reject" in prompt
