from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r"(?P<id>\d+)", "state.app.views.form_view"),
    (r"", "state.app.views.form_view"),
)
