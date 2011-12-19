# -*- coding: utf-8 -*-


"""
This module implements a simple threading worker pool.

Example:
    class MyThread(WorkerThread):
        def process(self, item, num):
            self.pool.log_debug("[%4s/%4s] Processing: %s" % (num, self.pool.queue_total, item))
            # process the *item*

    logger = ...
    pool = ThreadPool(logger=logger)

    # initialize threads
    for i in xrange(10):
        pool.add(MyThread(pool))

    pool.start()

    # populate the queue
    for i in xrange(100):
        pool.queue_put("item %s" % i)

    pool.stop()
"""


import sys
import threading
import Queue

import kobo.log


class WorkerThread(threading.Thread):
    get_timeout = 1

    def __init__(self, pool, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.pool = pool
        self.running = False
        self.kill = False
        self.failed = False

    def stop(self, kill=False):
        self.running = False # finish the work and join the thread
        self.kill = kill     # stop immediately without finishing the work
        self.join()

    def run(self):
        while (not self.kill) and (self.running or not self.pool.queue.empty()):
            try:
                item = self.pool.queue.get(timeout=self.get_timeout)
            except Queue.Empty:
                continue

            self.pool.queue_get_lock.acquire()
            self.pool.queue_processed += 1
            num = self.pool.queue_processed
            self.pool.queue_get_lock.release()

            try:
                self.process(item, num)
            except:
                self.failed = True
                self.pool.exceptions.append(sys.exc_info())
                self.pool.kill()

    def process(self, item, num):
        raise NotImplementedError


class ThreadPool(kobo.log.LoggingBase):
    def __init__(self, logger=None):
        kobo.log.LoggingBase.__init__(self, logger)
        self.threads = []
        self.exceptions = []
        self.queue = Queue.Queue()
        self.queue_put_lock = threading.Lock()
        self.queue_get_lock = threading.Lock()
        self.queue_total = 0
        self.queue_processed = 0

    def queue_put(self, item):
        """Put an item to the queue. Use this method instead of self.queue.put()."""
        self.queue.put(item)
        self.queue_put_lock.acquire()
        self.queue_total += 1
        self.queue_put_lock.release()

    def add(self, thread):
        self.threads.append(thread)

    def start(self):
        for i in self.threads:
            i.running = True
            i.kill = False
            i.start()

    def stop(self):
        for i in self.threads:
            i.running = False
        for i in self.threads:
            i.join()
        if self.exceptions:
            exc_info = self.exceptions[0]
            raise exc_info[0], exc_info[1], exc_info[2]

    def kill(self):
        for i in self.threads:
            i.kill = True
            i.running = False
