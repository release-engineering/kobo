# -*- coding: utf-8 -*-


from kobo.django.menu import MenuItem


menu = (
    MenuItem("Arches", "arch/list"),
    MenuItem("Channels", "channel/list"),
    MenuItem("Users", "user/list"),
    MenuItem("Workers", "worker/list"),
)
