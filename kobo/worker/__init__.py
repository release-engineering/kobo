# -*- coding: utf-8 -*-


from __future__ import absolute_import
from .taskmanager import TaskContainer
from .task import *

from . import tasks


TaskContainer.register_module(tasks)
