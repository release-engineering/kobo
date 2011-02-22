# -*- coding: utf-8 -*-


from kobo.plugins import Plugin


class BrokenPlugin(Plugin):
    enabled = True
    raise RuntimeError()
