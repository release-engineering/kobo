# -*- coding: utf-8 -*-


import sys

import kobo.cli


__all__ = (
    "main",
)


# register default command plugins
#import kobo.client.commands
#CommandContainer.register_module(kobo.client.commands, prefix="cmd_")


def main():
    command_container = kobo.cli.CommandContainer()
    parser = kobo.cli.CommandOptionParser(command_container=command_container, add_username_password_options=True)
    parser.run()
    sys.exit(0)
