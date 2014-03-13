# -*- coding: utf-8 -*-

import time
import urllib2
try:
    import json
except ImportError:
    import simplejson as json

from kobo.client import ClientCommand


MIN_POLL_INTERVAL = 15

class Watch_Log(ClientCommand):
    """displays task logs incrementally"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s task_id" % self.normalized_name

        self.parser.add_option(
            "--type",
            default="stdout.log",
            action="store",
            help="Show log with this name, default is stdout.log"
        )

        self.parser.add_option(
            "--poll",
            default=MIN_POLL_INTERVAL,
            type="int",
            help="Interval how often server should be polled for new info (seconds >= %s)" % MIN_POLL_INTERVAL
        )

        self.parser.add_option(
            "--nowait",
            default=False,
            action="store_true",
            help="Return after fetching current logfile, don't wait until task finishes"
        )


    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error("Exactly one task id must be specified.")
        try:
            task_id = int(args[0])
        except ValueError:
            self.parser.error("Task ID should be an integer")

        if kwargs['poll'] < MIN_POLL_INTERVAL:
            self.parser.error("Poll interval has to be higher than %s." % MIN_POLL_INTERVAL)

        # HACK: We're presuming, that urls were not touched and that base_url
        # is also url of web ui. As we suppose that also task.urls were not
        # altered it should work.
        url = self.conf['HUB_URL'].replace('/xmlrpc', '') + '/task/%d/log-json/%s?offset=%d'
        offset = 0
        while True:
            data = json.loads(urllib2.urlopen(url % (task_id, kwargs['type'], offset)).read())
            print data['content'],
            if data['task_finished'] == 1 or kwargs['nowait']:
                 break
            offset = data['new_offset']
            time.sleep(kwargs['poll'])
