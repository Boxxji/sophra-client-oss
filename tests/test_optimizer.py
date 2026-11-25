import unittest
from types import SimpleNamespace

from sophra_client import SophraOptimizer, optimize_messages, wrap_openai


class TestSophraUniversalOptimizer(unittest.TestCase):
    def test_deduplicates_tool_loop_and_prunes_verbose_output(self):
        messages = [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Inspect server logs and fix the crash."},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "function": {"name": "read_logs", "arguments": '{"lines":500}'}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "ERROR line detail " * 500},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c2", "function": {"name": "read_logs", "arguments": '{"lines":500}'}}]},
            {"role": "tool", "tool_call_id": "c2", "content": "ERROR line detail " * 500},
        ]
        res = optimize_messages(messages, model="gpt-4o", agent_id="py-coder")
        stats = res["optimization_stats"]
        self.assertTrue(res["allow_execution"])
        self.assertGreater(stats["duplicates_removed"], 0)
        self.assertGreater(stats["tool_outputs_pruned"], 0)
        self.assertGreater(stats["reduction_pct"], 50.0)
        self.assertGreater(stats["estimated_savings_usd"], 0)
        self.assertIn("[SOPHRA LOOP GUARD]", res["messages"][0]["content"])

    def test_triggers_hard_circuit_breaker_on_critical_loop(self):
        messages = [{"role": "user", "content": "Search docs"}]
        for i in range(5):
            messages.append({"role": "assistant", "content": "", "tool_calls": [{"id": f"t{i}", "function": {"name": "search", "arguments": '{"q":"error"}'}}]})
            messages.append({"role": "tool", "tool_call_id": f"t{i}", "content": "No results"})

        called = {"count": 0}
        opt = SophraOptimizer(agent_id="looping-agent")
        out = opt.guarded_call(
            model="claude-4-6-opus",
            messages=messages,
            call_fn=lambda m, msgs: called.__setitem__("count", called["count"] + 1),
            send_telemetry=False,
        )
        self.assertTrue(out["halted"])
        self.assertEqual(called["count"], 0)
        self.assertEqual(out["optimization"]["decision"], "CIRCUIT_BREAK_PAUSE")

    def test_compacts_middle_turns_and_finops_downgrades_model(self):
        messages = [{"role": "system", "content": "System prompt."}]
        for i in range(18):
            messages.append({"role": "user", "content": f"Step {i}: " + ("detailed context payload " * 60)})
            messages.append({"role": "assistant", "content": f"Answer {i}: " + ("analysis output " * 60)})

        res = optimize_messages(messages, model="claude-4-6-opus", max_input_tokens=3000, allow_model_switch=True)
        stats = res["optimization_stats"]
        self.assertEqual(res["decision"], "SWITCH_MODEL")
        self.assertEqual(res["model"], "claude-4-5-haiku")
        self.assertGreater(stats["middle_turns_compacted"], 10)
        self.assertLess(stats["tokens_after"], stats["tokens_before"])
        self.assertGreater(stats["estimated_savings_usd"], 0)

    def test_wrap_openai_drop_in_wrapper(self):
        captured = {}

        def fake_create(**kwargs):
            captured["model"] = kwargs["model"]
            captured["messages"] = kwargs["messages"]
            return {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60}}

        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
        wrapped = wrap_openai(fake_client, agent_id="any-openai-agent", smart_routing=True)
        resp = wrapped.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say hello in French."}],
        )
        self.assertEqual(resp["choices"][0]["message"]["content"], "ok")
        self.assertEqual(captured["model"], "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()
