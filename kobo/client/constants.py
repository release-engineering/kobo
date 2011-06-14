# -*- coding: utf-8 -*-


from kobo.types import Enum


__all__ = (
    "TASK_STATES",
    "FINISHED_STATES",
    "FAILED_STATES",
)


TASK_STATES = Enum(
    "FREE",        # default state for new tasks
    "ASSIGNED",    # assigned to a worker
    "OPEN",        # opened by a worker and being processed
    "CLOSED",      # successfully finished
    "CANCELED",    # canceled by user request
    "FAILED",      # failed
    "INTERRUPTED", # interrupted by an external event (power outage, process killed, etc.)
    "TIMEOUT",     # reached timeout and killed by task manager
    "CREATED",     # task is created, but still not ready to be processed
)


FINISHED_STATES = (
    TASK_STATES["CLOSED"],
    TASK_STATES["CANCELED"],
    TASK_STATES["FAILED"],
    TASK_STATES["INTERRUPTED"],
    TASK_STATES["TIMEOUT"],
)


FAILED_STATES = (
    TASK_STATES["CANCELED"],
    TASK_STATES["FAILED"],
    TASK_STATES["INTERRUPTED"],
    TASK_STATES["TIMEOUT"],
)
