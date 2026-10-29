from types import SimpleNamespace
from adversarial_ai_evals.model_client import (
    DEFENSE_PROMPT,
    AnthropicModelClient,
    OpenAIModelClient,
)


class RecordingMessages:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text="Hello "),
                SimpleNamespace(type="text", text="world"),
            ],
        )


def test_tool_response_sent_as_tool_result():
    messages = RecordingMessages()
    client = AnthropicModelClient(model_id="claude-test", client=SimpleNamespace(messages=messages))

    text = client.run_with_tool_response("summarize it", "DOCUMENT TEXT")

    assert text == "Hello world"
    sent = messages.kwargs
    assert sent["model"] == "claude-test"
    assert [tool["name"] for tool in sent["tools"]] == ["fetch_document"]
    user, assistant, tool_turn = sent["messages"]
    assert user == {"role": "user", "content": "summarize it"}
    tool_use = assistant["content"][0]
    assert tool_use["type"] == "tool_use"
    tool_result = tool_turn["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == tool_use["id"]
    assert tool_result["content"] == "DOCUMENT TEXT"


class RecordingCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Hello world"))])


def test_openai_tool_response_sent_as_tool_message():
    completions = RecordingCompletions()
    fake_openai = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    client = OpenAIModelClient(model_id="gpt-test", client=fake_openai)

    text = client.run_with_tool_response("summarize it", "DOCUMENT TEXT")

    assert text == "Hello world"
    sent = completions.kwargs
    assert sent["model"] == "gpt-test"
    assert [tool["function"]["name"] for tool in sent["tools"]] == ["fetch_document"]
    system, user, assistant, tool_turn = sent["messages"]
    assert system["role"] == "system"
    assert user == {"role": "user", "content": "summarize it"}
    tool_call = assistant["tool_calls"][0]
    assert tool_call["function"]["name"] == "fetch_document"
    assert tool_turn == {"role": "tool", "tool_call_id": tool_call["id"], "content": "DOCUMENT TEXT"}


def test_openai_empty_content_returns_empty_string():
    completions = RecordingCompletions()
    completions.create = lambda **kwargs: SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
    )
    client = OpenAIModelClient(client=SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    assert client.run_with_tool_response("summarize it", "DOCUMENT TEXT") == ""


def test_defense_prompt_only_when_enabled():
    messages = RecordingMessages()
    fake_anthropic = SimpleNamespace(messages=messages)
    AnthropicModelClient(client=fake_anthropic).run_with_tool_response("q", "doc")
    assert DEFENSE_PROMPT not in messages.kwargs["system"]
    AnthropicModelClient(client=fake_anthropic, defense=True).run_with_tool_response("q", "doc")
    assert DEFENSE_PROMPT in messages.kwargs["system"]

    completions = RecordingCompletions()
    fake_openai = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    OpenAIModelClient(client=fake_openai, defense=True).run_with_tool_response("q", "doc")
    assert DEFENSE_PROMPT in completions.kwargs["messages"][0]["content"]


def test_claude_verifier_parses_verdict():
    from adversarial_ai_evals.judge import ClaudeComplianceVerifier
    from adversarial_ai_evals.loader import load_attack_case

    case = load_attack_case("attacks/case_001.json")

    def verifier_saying(text):
        reply = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
        return ClaudeComplianceVerifier(
            client=SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: reply))
        )

    assert verifier_saying("COMPLIED").complied(case, "response")
    assert not verifier_saying("Resisted").complied(case, "response")
