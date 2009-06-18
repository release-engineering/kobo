# -*- coding: utf-8 -*-


from django.conf import settings
from django.core.urlresolvers import reverse


__all__ = (
    "Menu",
)


class Menu(object):
    """
    @summary: Menu object
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
            except:
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
        @return: active menu
        @rtype: dict
        """
        current_url = request.get_full_path()

        # list of submenu items matching current url
        matches = [ value for key, value in self.submenus.iteritems() if current_url.startswith(key) ]

        if not matches:
            return None

        # return the longest match
        matches.sort(lambda x, y: cmp(len(x["url"]), len(y["url"])), reverse=True)
        return matches[0]


    def get_current_menu(self, request):
        """
        @param request: http request object
        @type request: django.http.HttpRequest
        @return: dict with main menu, active menu and submenu of active menu
        @rtype: dict
        """
        
        active = self.find_active_menu(request)

        if active is None:
            return None

        return {
            "mainmenu": self.mainmenu,
            "active": active,
            "submenu": active["mainmenu"]["submenu"],
        }
