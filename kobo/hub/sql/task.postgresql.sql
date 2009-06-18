create index hub_task_archive_state on hub_task (state, archive) where archive=False;
analyze;
