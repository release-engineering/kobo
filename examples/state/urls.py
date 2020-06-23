from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', admin.site.urls),
    (r"(?P<id>\d+)", "state.app.views.form_view"),
    (r"", "state.app.views.form_view"),
)
