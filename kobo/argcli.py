import argparse
import sys

from kobo.plugins import Plugin


class ArgparseCommand(Plugin):
    """
    Base class for argparse-based commands.

    Commands must:
      - inherit from ArgparseCommand
      - implement add_arguments(self)
      - implement run(self, *args, **kwargs)
    """

    def __init__(self, parser):
        Plugin.__init__(self)
        self.parser = parser

    def add_arguments(self):
        """Register argparse arguments."""
        raise NotImplementedError

    def run(self, *args, **kwargs):
        """Execute command."""
        raise NotImplementedError


class CommandArgumentParser(object):
    """
    Argparse-based command dispatcher.

    This intentionally does NOT inherit from argparse.ArgumentParser.
    It is a coordinator that:
      - parses the global command name
      - dispatches to an argparse-capable command
    """

    def __init__(
        self,
        command_container,
        prog=None,
        default_command=None,
        default_profile=None,
    ):
        self.container = command_container
        self.default_command = default_command
        self.default_profile = default_profile

        self.parser = argparse.ArgumentParser(
            prog=prog,
            usage="%(prog)s <command> [args] [--help]",
            formatter_class=argparse.RawTextHelpFormatter,
        )

        self.parser.add_argument(
            "command",
            nargs="?",
            help="command to execute",
        )

        # everything after the command name
        self.parser.add_argument(
            "args",
            nargs=argparse.REMAINDER,
            help=argparse.SUPPRESS,
        )

    def _load_profile(self, profile):
        """
        Hook for loading a profile.
        Implemented here only as a placeholder.
        """
        pass

    def run(self, argv=None):
        cmd, cmd_ns, cmd_args = self.parse_args(argv)

        cmd_kwargs = vars(cmd_ns)

        # load profile if requested
        if self.default_profile and "profile" in cmd_kwargs:
            self._load_profile(cmd_kwargs["profile"])

        return cmd.run(*cmd_args, **cmd_kwargs)

    def parse_args(self, argv=None):
        argv = argv if argv is not None else sys.argv[1:]
        ns = self.parser.parse_args(argv)

        command_name = ns.command or self.default_command

        if not command_name:
            self.parser.error("no command specified")

        if command_name not in self.container.plugins:
            self.parser.error("unknown command: %s" % command_name)

        CommandClass = self.container[command_name]

        if not issubclass(CommandClass, ArgparseCommand):
            self.parser.error("command '%s' does not support argparse" % command_name)

        cmd_parser = argparse.ArgumentParser(
            prog="%s %s" % (self.parser.prog, command_name),
            formatter_class=argparse.RawTextHelpFormatter,
        )

        cmd_parser.container = self.container

        cmd = CommandClass(cmd_parser)
        cmd.add_arguments()

        # allow extra args (optparse compatibility)
        cmd_ns, remainder = cmd_parser.parse_known_args(ns.args)

        return cmd, cmd_ns, remainder
