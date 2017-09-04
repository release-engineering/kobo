# -*- coding: utf-8 -*-


from __future__ import absolute_import
from .taskmanager import TaskContainer

from . import tasks


TaskContainer.register_module(tasks)
