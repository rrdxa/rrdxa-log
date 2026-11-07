from django import forms
from django.db import models


class TimeText(models.TextField):
    """
    A PostgreSQL ``time`` column read as text.

    The schedule uses ``24:00:00`` ("midnight at the end of the day"), which
    ``datetime.time`` cannot represent, so psycopg raises ``DataError`` when
    decoding it.  Selecting the column as text avoids that.

    ``select_format()`` is only applied to SELECT (and GROUP BY) expressions,
    never to WHERE clauses, so filtering and ordering still use the native
    ``time`` value.
    """

    def select_format(self, compiler, sql, params):
        return f"{sql}::text", params

    def formfield(self, **kwargs):
        # TextField defaults to a Textarea; a time value wants a single line.
        kwargs.setdefault("widget", forms.TextInput)
        return super().formfield(**kwargs)
