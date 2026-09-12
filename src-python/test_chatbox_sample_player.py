"""No VRChat traffic: only in-memory playback and an ephemeral loopback receiver."""

import json
from pathlib import Path
import socket
import sys
from unittest.mock import Mock

import pytest
from pythonosc.osc_message import OscMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import chatbox_sample_player as player  # noqa: E402


CATALOG = Path(__file__).resolve().parents[1] / "tools/chatbox_samples"


def test_catalog_coverage_and_limits():
    samples = player.load_samples(CATALOG)
    languages = {s.language for s in samples} - {"mixed"}
    assert len(languages) == 20 and len(samples) >= 240
    assert len({s.id for s in samples}) == len(samples)
    assert min(s.units for s in samples) == 1
    assert max(s.units for s in samples) == 144
    assert max(s.text.count("\n") + 1 for s in samples) == 9
    for language in languages:
        assert {s.length for s in samples if s.language == language} == {"tiny", "short", "medium", "long"}


@pytest.mark.parametrize("text", ["", " \n ", "a" * 145, "🙂" * 73, "1\n" * 9,
                                 "bad\x00text", "bad\rtext", "bad\x1btext", "bad\u202etext"])
def test_invalid_samples_fail_instead_of_truncating(tmp_path, text):
    (tmp_path / "test.json").write_text(json.dumps({"en": [{"text": text}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        player.load_samples(tmp_path)


def test_emoji_boundary_and_newlines_preserved(tmp_path):
    text = "🙂" * 72
    (tmp_path / "test.json").write_text(json.dumps({"en": [{"text": text}, {"text": "a\n\nb"}]}), encoding="utf-8-sig")
    samples = player.load_samples(tmp_path)
    assert samples[0].units == 144 and samples[0].text == text
    assert samples[1].text == "a\n\nb"


def test_multilingual_osc_packet_has_actual_booleans_and_no_sound():
    text = "日本語 / مرحبا / café / 🙂\n第二行"
    packet = player.message_bytes(text)
    decoded = OscMessage(packet)
    assert decoded.address == "/chatbox/input"
    assert decoded.params == [text, True, False]
    assert decoded.params[1] is True and decoded.params[2] is False
    assert b",sTF\0" in packet


def test_pause_resume_quit_and_late_ticks_do_not_burst():
    now = [0]
    sent = []
    sample = player.Sample("en_001", "en", "Hi!", ())
    playback = player.Playback([sample], sent.append, interval=6, clock=lambda: now[0], emit=Mock())
    playback.tick()
    assert len(sent) == 1
    now[0] = 100
    playback.tick()
    playback.tick()
    assert len(sent) == 2
    playback.command("p")
    now[0] = 200
    playback.tick()
    assert len(sent) == 2
    playback.command("p")
    playback.tick()
    assert len(sent) == 2
    now[0] = 206
    playback.tick()
    assert len(sent) == 3
    playback.command("q")
    now[0] = 1000
    playback.tick()
    assert len(sent) == 3


def test_slow_send_starts_interval_after_completion():
    now = [0]
    send = Mock(side_effect=lambda sample: now.__setitem__(0, now[0] + 20))
    playback = player.Playback([player.Sample("en_001", "en", "Hi!", ())], send,
                               clock=lambda: now[0], interval=6)
    playback.tick()
    assert playback.deadline == 26
    playback.tick()
    assert send.call_count == 1


def test_seed_once_and_count_limit():
    samples = [player.Sample(f"en_{i:03}", "en", str(i), ()) for i in range(10)]
    a = player.Playback(samples, Mock(), seed=42)
    b = player.Playback(samples, Mock(), seed=42)
    assert a.order == b.order and {s.id for s in a.order} == {s.id for s in samples}
    now = [0]
    sent = []
    once = player.Playback(samples[:2], sent.append, ordered=True, once=True, clock=lambda: now[0])
    once.tick()
    now[0] = 6
    once.tick()
    assert once.stopped and sent == samples[:2]
    limited = player.Playback(samples, Mock(), max_messages=1)
    limited.tick()
    assert limited.stopped and limited.count == 1


def test_dry_run_opens_no_socket_or_log(tmp_path, monkeypatch):
    monkeypatch.setattr(player, "base_directory", lambda: tmp_path)
    monkeypatch.setattr(player, "read_key", lambda: "")
    forbidden = Mock(side_effect=AssertionError("network must not be opened"))
    monkeypatch.setattr(socket, "socket", forbidden)
    assert player.main(["--samples", str(CATALOG), "--dry-run", "--max-messages", "1"]) == 0
    forbidden.assert_not_called()
    assert not (tmp_path / "sent_logs").exists()


def test_default_noninteractive_launch_cannot_send(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    forbidden = Mock(side_effect=AssertionError("network must not be opened"))
    monkeypatch.setattr(socket, "socket", forbidden)
    with pytest.raises(ValueError, match="--start"):
        player.main(["--samples", str(CATALOG)])
    forbidden.assert_not_called()


def test_real_udp_goes_only_to_test_receiver_and_logs_unicode(tmp_path, monkeypatch):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    text = "こんにちは🙂\nمرحبا"
    (sample_dir / "test.json").write_text(json.dumps({"mixed": [{"text": text}]}), encoding="utf-8")
    monkeypatch.setattr(player, "base_directory", lambda: tmp_path)
    monkeypatch.setattr(player, "read_key", lambda: "")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(2)
        port = receiver.getsockname()[1]
        assert port != 9000
        assert player.main(["--samples", str(sample_dir), "--port", str(port), "--start", "--max-messages", "1"]) == 0
        packet, _ = receiver.recvfrom(4096)
    assert OscMessage(packet).params == [text, True, False]
    logs = list((tmp_path / "sent_logs").glob("*.jsonl"))
    assert len(logs) == 1
    record = json.loads(logs[0].read_text(encoding="utf-8"))
    assert record["event"] == "udp_submitted" and record["text"] == text
    assert record["target"] == f"127.0.0.1:{port}"


@pytest.mark.parametrize("args", [["--interval", "nan"], ["--interval", "2"],
                                 ["--port", "0"], ["--max-messages", "-1"]])
def test_invalid_options(args):
    with pytest.raises(SystemExit):
        player.parse_args(args)


def test_missing_catalog_and_unknown_language_fail(tmp_path):
    with pytest.raises(ValueError, match="No sample"):
        player.load_samples(tmp_path)
    with pytest.raises(ValueError, match="Unknown languages"):
        player.main(["--samples", str(CATALOG), "--languages", "invalid", "--list"])
