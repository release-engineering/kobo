# -*- coding: utf-8 -*-


import sys
from optparse import OptionParser, Option
from xmlrpclib import Fault

from kobo.plugins import Plugin, PluginContainer


__all__ = (
    "Command",
    "CommandContainer",
    "CommandOptionParser",
    "Option",
    "username_prompt",
    "password_prompt",
    "yes_no_prompt",
    "are_you_sure_prompt",
)


def username_prompt(prompt=None, default_value=None):
    """Ask for a username."""
    if default_value is not None:
        return default_value

    prompt = prompt or "Enter your username: "
    print >>sys.stderr, prompt,
    return sys.stdin.readline()


def password_prompt(prompt=None, default_value=None):
    """Ask for a password."""
    import getpass

    if default_value is not None:
        return default_value

    prompt = prompt or "Enter your password: "
    try:
        # try to use stderr stream
        result = getpass.getpass(prompt, stream=sys.stderr)
    except TypeError:
        # fall back to stdout
        result = getpass.getpass(prompt)
    return result


def yes_no_prompt(prompt, default_value=None):
    """Give a yes/no (y/n) question."""
    if default_value is not None:
        if default_value not in ("Y", "N"):
            raise ValueError("Invalid default value: %s" % default_value)
        default_value = default_value.upper()

    prompt = "%s [%s/%s]: " % (prompt, ("y", "Y")[default_value == "Y"], ("n", "N")[default_value == "N"])
    print >>sys.stderr, prompt,

    while True:
        user_input = sys.stdin.readline().strip().upper()
        if user_input == "" and default_value is not None:
            user_input = default_value

        if user_input == "Y":
            return True
        if user_input == "N":
            return False


def are_you_sure_prompt(prompt=None):
    """Give a yes/no (y/n) question."""
    prompt = prompt or "Are you sure? Enter 'YES' to continue: "
    print >>sys.stderr, prompt,
    user_input = sys.stdin.readline().strip()

    if user_input == "YES":
        return True

    return False


class Command(Plugin):
    """An abstract class representing a command for CommandOptionParser."""

    __slots__ = (
        "container",
        "parser",
        "normalized_name",
        "admin",
    )

    enabled = False
    admin = False


    username_prompt = staticmethod(username_prompt)
    password_prompt = staticmethod(password_prompt)
    yes_no_prompt = staticmethod(yes_no_prompt)
    are_you_sure_prompt = staticmethod(are_you_sure_prompt)


    def __init__(self, container, parser):
        Plugin.__init__(self)
        self.container = container
        self.parser = parser
        self.normalized_name = self.container.normalize_name(self.__class__.__name__)


    def options(self):
        """Add options to self.parser."""
        pass


    def run(self, *args, **kwargs):
        """Run a command. Arguments contain parsed options."""
        raise NotImplementedError()


class CommandContainer(PluginContainer):
    """Container for Command classes."""

    @classmethod
    def normalize_name(cls, name):
        """Replace some characters in command names."""
        return name.lower().replace('_', '-').replace(' ', '-')


class CommandOptionParser(OptionParser):
    """Enhanced OptionParser with plugin support."""
    def __init__(self,
            usage=None,
            option_list=None,
            option_class=Option,
            version=None,
            conflict_handler="error",
            description=None,
            formatter=None,
            add_help_option=True,
            prog=None,
            command_container=None,
            default_command=None):

        usage = usage or "%prog <command> [args] [--help]"
        self.container = command_container
        self.default_command = default_command or "help"
        self.command = None
        OptionParser.__init__(self, usage, option_list, option_class, version, conflict_handler, description, formatter, add_help_option, prog)


    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        file.write(self.format_help())
        if self.command is None or self.command == "help":
            file.write("\n")
            file.write(self.format_help_commands())


    def format_help_commands(self):
        result = []
        result.append("commands:")
        for name, plugin in sorted(self.container.plugins.iteritems()):
            admin = (" ", "A")[getattr(plugin, "admin", False)]
            result.append("%s %-30s %s" % (admin, name, plugin.__doc__ or ""))
        result.append("")
        return "\n".join(result)


    def parse_args(self, args=None, values=None):
        """return (command_instance, opts, args)"""
        args = self._get_args(args)
        command = None

        if len(args) > 0 and not args[0].startswith("-"):
            command = args[0]
            args = args[1:]
        else:
            command = self.default_command
            # keep args as is

        if not command in self.container.plugins:
            self.error("unknown command: %s" % command)

        CommandClass = self.container[command]
        cmd = CommandClass(self.container, self)
        if self.command != cmd.normalized_name:
            self.command = cmd.normalized_name
            cmd.options()
        cmd_opts, cmd_args = OptionParser.parse_args(self, args, values)
        return (cmd, cmd_opts, cmd_args)


    def run(self, args=None, values=None):
        """parse arguments and run a command"""
        cmd, cmd_opts, cmd_args = self.parse_args(args, values)
        cmd_kwargs = cmd_opts.__dict__
        try:
            cmd.run(*cmd_args, **cmd_kwargs)
        except Fault, ex:
            print "Exception: %s" % ex.faultString
        except Exception, ex:
            raise
            print "Exception: %s" % ex


class Help(Command):
    """show this help message and exit"""
    enabled = True


    def options(self):
        pass


    def run(self, *args, **kwargs):
        self.parser.print_help()


CommandContainer.register_plugin(Help)
