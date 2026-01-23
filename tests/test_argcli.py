import kobo.client
from kobo.argcli import CommandArgumentParser
from tests.plugins import commands


class FakeCommandContainer(kobo.client.ClientCommandContainer):
    pass


FakeCommandContainer.register_module(commands, prefix="cmd_")


class FakeCommandArgumentParser(CommandArgumentParser):
    def load_pub_profile(self, profile=None):
        pass


def test_argparse_command_registered_via_module():
    conf = kobo.conf.PyConfigParser()
    container = FakeCommandContainer(conf)

    parser = FakeCommandArgumentParser(
        command_container=container,
        default_profile="default-profile",
    )

    parser.run(["cmd-fake-echo", "hello", "world"])

    assert container.result == ["hello", "world"]
