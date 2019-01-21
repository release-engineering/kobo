from django.conf.urls import url, include
from django.contrib import admin
from django.http import HttpResponse


def home(request):
    return HttpResponse("Index", status=200, content_type="text/plain")


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r"^auth/", include("kobo.hub.urls.auth")),
    url(r"^home/$", home, name="home/index"),
    url(r"^task/", include("kobo.hub.urls.task")),
    url(r"^info/arch/", include("kobo.hub.urls.arch")),
    url(r"^info/channel/", include("kobo.hub.urls.channel")),
    url(r"^info/user/", include("kobo.hub.urls.user")),
    url(r"^info/worker/", include("kobo.hub.urls.worker")),
]
