from purchase_office.llm import FakeLLMClient, LLMClient


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
