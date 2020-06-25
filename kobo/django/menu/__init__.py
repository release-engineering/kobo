# -*- coding: utf-8 -*-


"""
This is a menu system for django applications.

It creates 'menu' object which provides access
to functions for manipulation with html menu.

To set the menu up, follow steps below:


1) create project/menu.py
-------------------------
from kobo.django.menu import MenuItem, include
menu = (
    MenuItem("MenuItem-1", "/url/path/", absolute_url=True, menu=(
        MenuItem("MenuItem-1.1", "/url/path/1/", absolute_url=True),
        MenuItem("MenuItem-1.2", "/url/path/2/", absolute_url=True),
    )),
    MenuItem("MenuItem-2", "url_label", ("Developers",), ("app.change_data",)),
    include("project.app.menu"),
    MenuItem.include("project.another_app.menu"),
)

# In this example is MenuItem-1 and it's submenu tree accessible for anybody.
# MenuItem-2 is only for users in group Developers with specific permission.
# Instead of specifying complete tree in one file, you can use include()
# command in similar way as it is used in urls.py (see third menu item).
# include() function is also a staticmethod of MenuItem class (see fourth menu item).
#
# If you leave title empty, the menu item will serve as a delimiter. In such a
# case you can also omit the url.

# can be specified only once in project-wide menu
css_active_class = "active_menu"


2) modify settings.py
---------------------
# set the menu root
ROOT_MENUCONF = "project.menu"

# add menu middleware
MIDDLEWARE_CLASSES = (
    ...
    "kobo.django.menu.middleware.MenuMiddleware",
    ...
)

# add a context processor to add 'menu' variable to each request
TEMPLATE_CONTEXT_PROCESSORS = (
    ...
    "kobo.django.menu.context_processors.menu_context_processor",
    ...
)


3) add menu to a html template
------------------------------
# The simplest use in template is just to display menu as {{ menu }}.
# Default format is nested ul list.
# Active menus/submenus will be tagged with css_active_class.
# Delimiters will be rendered as empty list items with class `delimiter`.

# If you need another approach, you can access directly to all menu items
# and display menu parts by yourself:

# display all menu items from main menu
{% for m in menu.items %}
  {{ m.as_a }}
{% endfor %}

# Delimiters rendered with `as_a` return empty string, so are invisible.

# menu.levelX = active menu item on Xth level
# menu.levelX.items = all visible menu items of the ^^^ menu
{% for m in menu.level1.items %}
  {{ m.as_a }}
{% endfor %}

# If you are using Bootstrap and want to include the menu in a navbar, there is
# a method to render the menu in this way. Note however that in this case you
# can only use one level of nesting. The top level items will be rendered
# directly in the navbar, their children will form a dropdown menu and their
# grand children will be ignored.
{{ m.as_bootstrap_navbar_dropdown_menu }}
"""

import six

from six.moves import range
from six import python_2_unicode_compatible

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from kobo.django.django_version import django_version_ge
if django_version_ge('1.10.0'):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

try:
    from django.utils.encoding import smart_unicode as smart_text
except ImportError:
    from django.utils.encoding import smart_text


__all__ = (
    "include",
    "menu",
    "MenuItem",
)


def include(module):
    """helper function to load nested menus"""
    m = __import__(module, {}, {}, [""])
    return m.menu


@python_2_unicode_compatible
class MenuItem(object):
    """basic menu item - every menuitem can have submenu collections of
    these. Only main menu is special instance of Menu class."""

    # bind include() to the class
    include = staticmethod(include)

    def __init__(self, title, url, acl_groups=None, acl_perms=None, absolute_url=False, menu=None):
        self.title = smart_text(title)
        self._url = url
        self._url_is_resolved = absolute_url
        self.absolute_url = absolute_url
        self.acl_groups = acl_groups and set(acl_groups) or set()
        self.acl_perms = acl_perms and set(acl_perms) or set()
        self.main_menu = None
        self.parent_menu = None
        self.alters_data = False

        self.submenu_list = []
        for i in menu or []:
            if type(i) in (tuple, list):
                self.submenu_list.extend(i)
            else:
                self.submenu_list.append(i)

        self.active = False
        self.depth = 0

    def __repr__(self):
        return "<MenuItem>: %s (%s)" % (self.title, self.url)

    def __len__(self):
        return len(self.url)

    def __str__(self):
        if self.title == "":
            return mark_safe(u"<li class='divider'></li>")
        result = ""
        if self.items:
            result = u"<ul>%s</ul>" % u"".join([six.text_type(i) for i in self.items])
        return mark_safe(u"<li>%s%s</li>" % (self.as_a(), result))

    @property
    def url(self):
        if self._url and not self._url_is_resolved:
            self._url = reverse(self._url)
        self._url_is_resolved = True
        return self._url

    def as_a(self):
        if not self.visible:
            return u""

        if self.active and self.main_menu.css_active_class:
            style = u" class='%s'" % self.main_menu.css_active_class
        else:
            style = u""

        if self.url:
            result = u"<a href='%s'%s>%s</a>" % (self.url, style, self.title)
        else:
            result = six.text_type(self.title)

        return mark_safe(result)

    @property
    def items(self):
        return [i for i in self.submenu_list if i.visible]

    @property
    def first_item(self):
        if self.items:
            return self.items[0]
        return None

    @property
    def last_item(self):
        if self.items:
            return self.items[-1]
        return None

    @property
    def inner_items(self):
        return self.items[1:-1]

    def setup_menu_tree(self, mainmenu_obj):
        if mainmenu_obj != self:
            self.main_menu = mainmenu_obj

        actual_depth = self.depth

        if self.submenu_list:
            mainmenu_obj.depth = max(mainmenu_obj.depth, actual_depth + 1)

        for i in self.submenu_list:
            i.parent_menu = self
            i.depth = actual_depth + 1
            i.setup_menu_tree(mainmenu_obj)
            mainmenu_obj.cached_menuitems.append(i)

    def set_active(self, active):
        self.active = active
        if self.parent_menu is not None:
            self.parent_menu.set_active(active)

    @property
    def visible(self):
        # return False if field should be displayed to user
        if self.main_menu.user.is_superuser:
            return True

        if self.acl_groups:
            if self.acl_groups.intersection(self.main_menu.acl_groups):
                return True
            return False

        if self.acl_perms:
            for perm in self.acl_perms:
                if perm not in self.main_menu.acl_perms:
                    self.main_menu.acl_perms[perm] = self.main_menu.user.has_perm(perm)
                if self.main_menu.acl_perms[perm]:
                    return True
            return False

        return True

    def as_li(self):
        """Render menu item as a list item."""
        if not self.title:
            return mark_safe('<li class="divider"></li>')
        return mark_safe('<li>%s</li>' % self.as_a())

    def as_bootstrap_navbar_dropdown_menu(self):
        """
        Render menu item as a list with a possible dropdown. Note that any
        items nested under children of this item are ignored.
        """
        cls = ''
        sub = ''
        link = self.as_a()
        if self.items:
            link = '<a href="%s" class="dropdown-toggle" data-toggle="dropdown">%s <span class="caret"></span></a>' % (self.url, self.title)
            sub = ''.join([i.as_li() for i in self.items])
            sub = '<ul class="dropdown-menu" role="menu">%s</ul>' % sub
            cls = ' class="dropdown"'

        return mark_safe('<li%s>%s%s</li>' % (cls, link, sub))


@python_2_unicode_compatible
class MainMenu(MenuItem):

    def __init__(self, menu, css_active_class=None):
        MenuItem.__init__(self, "ROOT_MENU", "", absolute_url=True, menu=menu)
        self.user = None
        self.path = ""
        self.cached_menuitems = []
        self.css_active_class = css_active_class or ""
        self.active = None # reference to active menu (overrides MenuItem behavior)

        # set main_menu references, compute menu depth
        self.setup_menu_tree(self)

    def __repr__(self):
        return "<MainMenu>: %s" % (self.path)

    def __str__(self):
        """Return menu as printable <ul> list."""
        return mark_safe(u"<ul>%s</ul>" % "".join([six.text_type(i) for i in self.items]))

    def as_bootstrap_navbar_dropdown_menu(self):
        """
        Return menu as a printable <ul> list appropriate for use in Bootstrap
        navbar. Only one level nesting is supported and the nested items are
        rendered as dropdown menus.
        """
        content = ''.join([i.as_bootstrap_navbar_dropdown_menu() for i in self.items])
        return mark_safe('<ul class="nav navbar-nav">%s</ul>' % content)

    def __getattr__(self, name):
        # get specified submenu level in active menu
        if not name.startswith("level"):
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        try:
            level = int(name[5:])
        except ValueError:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        if level not in list(range(1, self.depth + 1)):
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        if not self.active:
            return None

        if self.active.depth < level:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

        menu = self.active
        while menu.depth > level:
            menu = menu.parent_menu
        return menu

    def setup(self, request):
        self.user = request.user
        self.path = request.get_full_path()
        self.acl_groups = set([i.name for i in request.user.groups.all().only("name")])
        self.acl_perms = {}
        self.find_active_menu()
        return self

    def find_active_menu(self):
        if self.active:
            # reset cached active path
            self.active.set_active(False)

        matches = [i for i in self.cached_menuitems if i.visible and i.url and self.path.startswith(i.url)]
        if not matches:
            self.active = None
            return None

        # find the longest menu match
        matches.sort(key=len, reverse=True)
        found = matches[0]
        found.set_active(True)
        self.active = found
        return found


# load menu configuration from project
if not hasattr(settings, "ROOT_MENUCONF"):
    raise ImproperlyConfigured("'ROOT_MENUCONF' is needed in settings to run kobo.django.menu app.")
menu_module = __import__(settings.ROOT_MENUCONF, {}, {}, [""])
menu = MainMenu(menu_module.menu, getattr(menu_module, "css_active_class", ""))
