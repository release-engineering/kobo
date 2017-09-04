# -*- coding: utf-8 -*-


from __future__ import absolute_import
import os

from .task import *
from .taskmanager import *

from . import tasks


TaskContainer.register_module(tasks)
