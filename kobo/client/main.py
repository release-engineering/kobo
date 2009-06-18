# -*- coding: utf-8 -*-


import sys
from optparse import Option, IndentedHelpFormatter

from kobo.cli import CommandOptionParser, CommandContainer


__all__ = (
    "main",
)


# register default command plugins
#import kobo.client.commands
#CommandContainer.register_module(kobo.client.commands, prefix="cmd_")


def main():
    command_container = CommandContainer()

    option_list = [
        Option("--username", help="specify user"),
        Option("--password", help="specify password"),
    ]

    formatter = IndentedHelpFormatter(max_help_position=60, width=120)
    parser = CommandOptionParser(command_container=command_container, default_command="help", formatter=formatter)
    parser._populate_option_list(option_list, add_help=False)
    parser.run()
    sys.exit(0)
