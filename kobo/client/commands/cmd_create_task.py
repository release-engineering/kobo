# -*- coding: utf-8 -*-


import simplejson

from kobo.client import ClientCommand


class Create_Task(ClientCommand):
    """create a new task which is either brand new or based on existing one"""
    enabled = True
    admin = True

    def options(self):
        self.parser.usage = "%%prog %s <options>" % self.normalized_name

        # if not specified, value from source task is used
        self.parser.add_option("--clone-from", dest="task_id", type="int", help="a task ID to clone a new task from")
        self.parser.add_option("--args", help="task arguments in JSON serialized dictionary")
        self.parser.add_option("--owner", dest="owner_name", help="username of the task owner")
        self.parser.add_option("--worker", dest="worker_name", help="name (hostname) of the worker")
        self.parser.add_option("--label", help="label or description")
        self.parser.add_option("--method", help="method name of the task handler")
        self.parser.add_option("--comment", help="comment")
        self.parser.add_option("--arch", dest="arch_name", help="arch name")
        self.parser.add_option("--channel", dest="channel_name", help="channel name")
        self.parser.add_option("--timeout", help="timeout")
        self.parser.add_option("--priority", help="priority")
        self.parser.add_option("--weight", help="weight")

    def _check_task_args(self, task_args):
        try:
            arg_dict = simplejson.loads(task_args)
        except ValueError:
            self.parser.error("Arguments have to be specified in valid JSON.")

        if type(arg_dict) != dict:
            self.parser.error("Arguments have to be specified in dictionary type.")

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        task_args = kwargs.get("args", None)
        if task_args != None:
            self._check_task_args(task_args)

        if kwargs["task_id"] is None:
            if kwargs["owner_name"] is None:
                self.parser.error("Owner is not set.")
            if kwargs["method"] is None:
                self.parser.error("Method is not set.")

        for key, value in kwargs.items():
            if value is None:
                del kwargs[key]

        self.set_hub(username, password)
        self.hub.client.create_task(kwargs)
