from kobo.argcli import ArgparseCommand

__all__ = ("Cmd_Fake_Echo",)


class Cmd_Fake_Echo(ArgparseCommand):
    enabled = True
    name = "fake-echo"

    def add_arguments(self):
        self.parser.add_argument("words", nargs="+")

    def run(self, *args, **kwargs):
        # store result on container
        self.parser.container.result = kwargs["words"]
