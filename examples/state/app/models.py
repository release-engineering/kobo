from kobo.django.fields import StateEnumField
from django.db import models
from workflow import workflow
import six


class SimpleState(models.Model):
    state = StateEnumField(workflow, default="NEW", null=False)
    comment = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super(SimpleState, self).save(*args, **kwargs)
        if self.state._to:
            self.state.change_state(None, commit=True)

    def __unicode__(self):
        return six.text_type(self.state._current_state)
