# -*- coding: utf-8 -*-


"""
CommandOptionParser HOWTO
=========================

1) setup CommandContainer
-------------------------
# In case you don't need any special functionality, just import default CommandContainer.
# Otherwise it's recommended to inherit your own container and extend it's functionality.
# Typical use cases are shared configuration or shared XML-RPC connection.

from kobo.cli import CommandContainer
class MyCommandContainer(CommandContainer):
    def __init__(self, *args, **kwargs):
        CommandContainer.__init__(self, *args, **kwargs)
        self.xmlrpc_client = ...


2) write your own Commands
--------------------------
# It usually makes sense to inherit directly from Command class.
# All common methods and attributes should be in the container.
# Specify command arguments in the options() method using add_argument().
# ArgumentParser.parse_args() result is automatically passed to run(*args, **kwargs) method.
# An ArgumentParser instance is available in self.parser attribute.

class Make_Dirs(Command):
    '''create directories'''
    enabled = True
    admin = False

    def options(self):
        self.parser.usage = "%(prog)s %s [options] <user>" % self.normalized_name
        self.parser.add_argument("-m", "--mode", help="set directory perms (0xxx)")

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a directory")
        mode = kwargs.pop("mode", "0755")
        mode = int(mode, 0) # convert oct string to int

        import os
        for directory in args:
            os.makedirs(directory, mode=mode)


3) register commands to a container
-----------------------------------
# Register either either all plugins (register_plugin)
# or all plugins in a module (register_module) to a container.
# All plugins must have enabled=True otherwise they won't be registered.

(My)CommandContainer.register_plugin(plugin_class)
(My)CommandContainer.register_module(module_with_plugins)


4) Use CommandOptionParser
--------------------------
command_container = (My)CommandContainer()
parser = CommandOptionParser(command_container=command_container)
parser.run()

# See kobo.client.main for slightly advanced example.
"""


from __future__ import print_function
import sys
import argparse
import datetime
from six.moves.xmlrpc_client import Fault

from kobo.plugins import Plugin, PluginContainer
from kobo.shortcuts import force_list
import six
import os.path

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
    print(prompt, end=' ', file=sys.stderr)
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
    print(prompt, end=' ', file=sys.stderr)

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
    print(prompt, end=' ', file=sys.stderr)
    user_input = sys.stdin.readline().strip()

    if user_input == "YES":
        return True

    return False


class Command(Plugin):
    """An abstract class representing a command for CommandOptionParser."""

    enabled = False
    admin = False

    username_prompt = staticmethod(username_prompt)
    password_prompt = staticmethod(password_prompt)
    yes_no_prompt = staticmethod(yes_no_prompt)
    are_you_sure_prompt = staticmethod(are_you_sure_prompt)

    def __init__(self, parser):
        Plugin.__init__(self)
        self.parser = parser

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


class CommandOptionParser(argparse.ArgumentParser):
    """Enhanced OptionParser with plugin support."""
    def __init__(self,
            usage=None,
            version=None,
            conflict_handler="error",
            description=None,
            formatter_class=None,
            add_help=True,
            prog=None,
            command_container=None,
            default_command="help",
            add_username_password_options=False,
            add_hub_option=False,
            default_profile="",
            configuration_directory="/etc"):
        usage = usage or "%(prog)s <command> [args] [--help]"
        self.container = command_container
        self.default_command = default_command
        self.command = None
        formatter_class = formatter_class or argparse.RawTextHelpFormatter

        # Initialize the argument parser
        super(CommandOptionParser, self).__init__(
            prog=prog,
            usage=usage,
            description=description,
            conflict_handler=conflict_handler,
            add_help=add_help,
            formatter_class=formatter_class,
        )

        # Add version argument if provided
        if version:
            self.add_argument('--version', action='version', version=version)

        if add_username_password_options:
            self._add_opts(
                ["--username", "specify user"],
                ["--password", "specify password"]
            )

        if add_hub_option:
            self._add_opts(["--hub", "specify URL of XML-RPC interface on hub"])

        if default_profile:
            self.default_profile = default_profile

            self._add_opts(
                ["--profile", "specify profile (default: {0})".format(self.default_profile)]
            )
        else:
            self.default_profile = ""

        self.configuration_directory = configuration_directory

    def print_help(self, file=None, admin=False):
        if file is None:
            file = sys.stdout
        file.write(self.format_help())
        if self.command in (None, "help", "help-admin"):
            file.write("\n")
            file.write(self.format_help_commands(admin=admin))

    def format_help_commands(self, admin=False):
        commands = []
        admin_commands = []

        for name, plugin in sorted(six.iteritems(self.container.plugins)):
            is_admin = getattr(plugin, "admin", False)
            text = "  %-30s %s" % (name, plugin.__doc__ or "")
            if is_admin:
                if admin:
                    admin_commands.append(text)
            else:
                commands.append(text)

        if commands:
            commands.insert(0, "commands:")
            commands.append("")

        if admin_commands:
            admin_commands.insert(0, "admin commands:")
            admin_commands.append("")

        return "\n".join(commands + admin_commands)

    def parse_args(self, args=None, values=None):
        """return (command_instance, opts, args)"""
        args = args if args is not None else sys.argv[1:]
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
        cmd = CommandClass(self)
        if self.command != cmd.normalized_name:
            self.command = cmd.normalized_name
            cmd.options()

        # Parse arguments using argparse
        parsed_args = super(CommandOptionParser, self).parse_args(args)

        # Get remaining positional arguments (if any)
        remaining_args = getattr(parsed_args, 'args', [])

        return (cmd, parsed_args, remaining_args)

    def run(self, args=None):
        """parse arguments and run a command"""
        # Get command instance and parsed arguments
        cmd, parsed_args, remaining_args = self.parse_args(args)

        # Convert Namespace to dictionary for kwargs
        cmd_kwargs = vars(parsed_args)

        # Handle profile if specified
        if self.default_profile and 'profile' in cmd_kwargs:
            self._load_profile(cmd_kwargs['profile'])

        # Run command with positional args and keyword args
        cmd.run(*remaining_args, **cmd_kwargs)

    def _add_opts(self, *args):
        """populates one or more options with their respective help texts"""

        for option, help_text in args:
            # Strip leading dashes and use as destination
            dest = option.lstrip('-').replace('-', '_')
            self.add_argument(option, dest=dest, help=help_text)

    def _load_profile(self, profile):
        """load configuration file under location <CONFIGURATION_DIRECTORY>/<PROFILE>.conf"""
        if not profile:
            profile = self.default_profile

        configuration_file = os.path.join(self.configuration_directory, '{0}.conf'.format(profile))
        self.container.conf.load_from_file(configuration_file)

class Help(Command):
    """show this help message and exit"""
    enabled = True

    def options(self):
        pass

    def run(self, *args, **kwargs):
        self.parser.print_help(admin=False)


class Help_Admin(Command):
    """show help message about administrative commands and exit"""
    enabled = True

    def options(self):
        # override default --help option
        self.parser.add_argument(
            "--help",
            action="store_true",
            dest="help",
            help="show help message and exit"
        )

    def run(self, *args, **kwargs):
        self.parser.print_help(admin=True)


class Help_RST(Command):
    """print program usage as reStructuredText"""
    enabled = True

    def options(self):
        pass

    def run(self, *args, **kwargs):
        prog = self.parser.get_prog_name()
        print(".. -*- coding: utf-8 -*-\n")
        print("=" * len(prog))
        print(prog)
        print("=" * len(prog), "\n")

        # add subtitle (command description)
        description = getattr(self.parser.container, "_description", None)
        if description:
            print(":Subtitle: %s\n" % description)

        # add copyright
        copyright = getattr(self.parser.container, "_copyright", None)
        if copyright:
            print(":Copyright: %s" % copyright)

        # add date
        print(":Date: $Date: %s $\n" % datetime.datetime.strftime(datetime.datetime.utcnow(), format="%F %X"))

        print("--------")
        print("COMMANDS")
        print("--------")

        for command_name, CommandClass in sorted(self.parser.container.plugins.items()):
            parser = argparse.ArgumentParser(
                usage=self.parser.usage,
                formatter_class=argparse.RawTextHelpFormatter
            )
            cmd = CommandClass(parser)
            cmd.normalized_name = command_name
            cmd.options()
            cmd.container = self.parser.container

            print(command_name)
            print("-" * len(command_name))

            if cmd.admin:
                print("[ADMIN ONLY]", end=' ')

            print(cmd.__doc__.strip(), end="\n\n")
            
            # Get formatted usage
            usage = parser.format_usage()
            if usage:
                print(usage.replace("usage: ", "**Usage:** "), end="\n\n")

            # Process and display arguments
            for action in parser._actions:
                # Skip help action
                if action.dest == 'help':
                    continue

                # Format option strings
                opts = []
                for opt_str in action.option_strings:
                    if action.metavar:
                        opts.append(f"{opt_str}={action.metavar}")
                    elif action.nargs:
                        opts.append(f"{opt_str}={action.dest.upper()}")
                    else:
                        opts.append(opt_str)
                
                if opts:  # Optional arguments
                    print("/".join(opts))
                elif action.dest != 'help':  # Positional arguments
                    print(action.dest)
                
                # Print help text
                if action.help:
                    print(f"  {action.help}")
                
                # Show if argument can be specified multiple times
                if action.nargs in ('+', '*', argparse.REMAINDER):
                    print("\n  This option can be specified multiple times")
                print()
            print()

        # handle :Contact: and :Author: ourselves
        authors = force_list(getattr(self.parser.container, "_authors", []))
        contact = getattr(self.parser.container, "_contact", None)
        if authors or contact:
            print("-------")
            print("AUTHORS")
            print("-------")

            for author in sorted(authors):
                print("- %s\n" % author)

            if contact:
                print("**Contact:** %s\n" % contact)


CommandContainer.register_plugin(Help)
CommandContainer.register_plugin(Help_Admin)
CommandContainer.register_plugin(Help_RST)
