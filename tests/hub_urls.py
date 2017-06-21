from django.conf.urls import url, patterns, include

urlpatterns = patterns("",
    url(r"^auth/", include("kobo.hub.urls.auth")),
    url(r"^task/", include("kobo.hub.urls.task")),
    url(r"^info/arch/", include("kobo.hub.urls.arch")),
    url(r"^info/channel/", include("kobo.hub.urls.channel")),
    url(r"^info/user/", include("kobo.hub.urls.user")),
    url(r"^info/worker/", include("kobo.hub.urls.worker")),
)
