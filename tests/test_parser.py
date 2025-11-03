import argparse
import pytest
from kobo.cli import CommandOptionParser, CommandContainer, Command


class DummyCommand(Command):
    """dummy command"""

    enabled = True

    def options(self):
        self.parser.add_argument("--foo", help="foo option")

    def run(self, *args, **kwargs):
        self.called = True
        self.kwargs = kwargs


def test_parse_args():
    container = CommandContainer()
    container.register_plugin(DummyCommand)

    parser = CommandOptionParser(command_container=container)

    cmd, parsed_args, remaining = parser.parse_args(["dummycommand", "--foo", "x"])

    assert isinstance(cmd, DummyCommand)
    assert parsed_args.foo == "x"
    assert remaining == []


def test_run_executes_command(monkeypatch):
    container = CommandContainer()
    container.register_plugin(DummyCommand)
    parser = CommandOptionParser(command_container=container)

    called = {}

    def fake_parse_args(args=None):
        cmd = DummyCommand(parser)
        return cmd, argparse.Namespace(foo="X"), []

    monkeypatch.setattr(parser, "parse_args", fake_parse_args)

    DummyCommand.run = lambda self, *a, **kw: called.update(
        {"ran": True, "foo": kw["foo"]}
    )
    parser.run(["dummycommand", "--foo", "X"])

    assert called == {"ran": True, "foo": "X"}
