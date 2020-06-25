from __future__ import absolute_import
from kobo.django.fields import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.forms import ModelForm
from .models import SimpleState

class ModifyForm(ModelForm):
    class Meta:
        model = SimpleState

    def __init__(self, *args, **kwargs):
        super(ModifyForm, self).__init__(*args, **kwargs)
        self.fields['state'].choices = self.instance.state.get_next_states_mapping() # user=xxx

    def save(self, *args, **kwargs):
        commit = kwargs.get('commit', True) # default django commit is True
        self.instance.state.change_state(self.cleaned_data["state"], commit=commit)
        return super(ModifyForm, self).save(*args, **kwargs)

def form_view(request, id=None):
    if request.POST:
        if id:
            form = ModifyForm(request.POST, instance=SimpleState.objects.get(id=id))
        else:
            form = ModifyForm(request.POST)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect('.')
    else:
        if id:
            form = ModifyForm(instance=SimpleState.objects.get(id=id))
        else:
            form = ModifyForm()

    return render(request, 'test.html', {'form': form})
