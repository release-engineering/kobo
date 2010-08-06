#!/usr/bin/python


import django.db
from django.db import connections
from django.db.models import get_models
from django.core.management.color import no_style


def reset_sequences(connection, cursor, models=None):
    models = models or get_models(include_auto_created=True)
    for sql in connection.ops.sequence_reset_sql(no_style(), models):
        cursor.execute(sql)


if __name__ == "__main__":
    for model in get_models(include_auto_created=True):
        db_for_write = django.db.router.db_for_write(model)
        connection = connections[db_for_write]
        cursor = connection.cursor()
        reset_sequences(connection, cursor, models=[model])
