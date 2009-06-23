# -*- coding: utf-8 -*-


from django.conf import settings
from django.core.urlresolvers import reverse


__all__ = (
    "Menu",
)


class Menu(object):
    """
    @summary: Menu class which generates mainmenu and submenus for Django apps.
    """

    __slots__ = (
        "mainmenu",
        "submenus",
    )

    def __init__(self, request):
        """
        @param request: http request object
        @type request: django.http.HttpRequest
        """
        self.mainmenu = []
        self.submenus = {}

        for app_name in settings.INSTALLED_APPS:
            if app_name.startswith("django."):
                continue

            try:
                menu_module = __import__("%s.menu" % app_name, {}, {}, [""])
            except ImportError:
                continue

            mainmenu_item = {
                "url": reverse(menu_module.url),
                "label": menu_module.label,
                "order": menu_module.order,
                "submenu": [],
            }

            self.mainmenu.append(mainmenu_item)

            for i in menu_module.submenu:
                submenu_item = {
                    "url": reverse(i["url"]),
                    "label": i["label"],
                    "mainmenu": mainmenu_item,
                }
                mainmenu_item["submenu"].append(submenu_item)
                self.submenus[submenu_item["url"]] = submenu_item

            self.mainmenu.sort(lambda x, y: cmp(x["label"], y["label"]))
            self.mainmenu.sort(lambda x, y: cmp(x["order"], y["order"]))


    def find_active_menu(self, request):
        """
        @param request: http request object
        @type request: django.http.HttpRequest
        @return: (active mainmenu, active submenu)
        @rtype: (dict, dict)
        """
        current_url = request.get_full_path()

        # list of submenu items matching current url
        submenu_matches = [ value for key, value in self.submenus.iteritems() if current_url.startswith(key) ]

        if submenu_matches:
            # find the longest submenu match
            submenu_matches.sort(lambda x, y: cmp(len(x["url"]), len(y["url"])), reverse=True)
            submenu = submenu_matches[0]
            return submenu["mainmenu"], submenu

        mainmenu_matches = [ i for i in self.mainmenu if current_url.startswith(i["url"]) ]
        # find the longest mainmenu match
        mainmenu_matches.sort(lambda x, y: cmp(len(x["url"]), len(y["url"])), reverse=True)
        if mainmenu_matches:
            mainmenu = mainmenu_matches[0]
            return mainmenu, None

        return None, None


    def get_current_menu(self, request):
        """
        @param request: http request object
        @type request: django.http.HttpRequest
        @return: dict with main menu, active menu and submenu of active menu
        @rtype: dict
        """

        active_mainmenu, active_submenu = self.find_active_menu(request)

        if active_mainmenu is None:
            return None

        return {
            "mainmenu": self.mainmenu,
            "submenu": active_mainmenu["submenu"],
            "active_mainmenu": active_mainmenu,
            "active_submenu": active_submenu,
        }
