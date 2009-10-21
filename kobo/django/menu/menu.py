# -*- coding: utf-8 -*-


'''
Menu system for django applications. It creates Menu object which provides
access to most used functions for working with html menu. Simplest use case
is to define project wide menu in file project/menu.py in this format:

menu = (
    (<title>, <url>, (<user_group>, ...), (<user_perm>, ...), (<menu>, ...),
)

then you have to set
ROOT_MENUCONF = 'project.menu'
in your settings.py. Of course you can use another path and module to store
it. This setting has no default value.

example is:
menu = (
    ("Menu item 1", "/url/path/", (), (), (
        ("Submenu 1a", "/url/path/1/", (), (), ()),
        ("Submenu 1b", "/url/path/2/", (), (), ()),
    ),
    ("Menu item 2", reverse('url_label'), ('Developers',), ('app.change_data',), ()),
    include('project.app'),
)
css_active_class = "active_menu" # can be specified only once in project-wide
menu

In this example is first submenu tree accessible for anybody, second only for
users in group Developers with specific permission.

Instead of specifying complete tree in one file, you can use include()
command in similar way as it is used in urls.py. It is used as third submenu
in the example.

Second step is to add 'kobo.django.menu.middleware.MenuMiddleware' to
MIDDLEWARE_CLASSES in project's settings.py.

From now request.menu is accesible in every page call.

For convenience kobo.django.menu.context_processors.menu_context_processor is
provided. If you add it to your CONTEXT_PROCESSORS, menu object will be
accessible in any processed template in 'menu' context variable.

Simplest use in template is just to display menu as {{menu}}. Default format
is nested ul list. Active menus/submenus will be tagged with
css_active_class.

If you need some other approach, you are provided with access to menu.items,
etc. and you can display menu parts by yourself.

'''

__all__ = (
    "Menu",
    "menu",
    'include',
)

def include(module):
    '''helper function to load nested menus'''
    m = __import__(module, {}, {}, [""])
    return m.menu

class MenuItem(object):
    '''basic menu item - every menuitem can have submenu collections of
    these. Only main menu is special instance of Menu class.'''
    def __init__(self, title, url, acl_groups, acl_perms, main_menu, parent_menu = None):
        self.depth = 0
        self.url = url
        self.title = title
        self.acl_groups = set(acl_groups)
        self.acl_perms = set(acl_perms)
        self.main_menu = main_menu
        self.parent = parent_menu
        self.submenu = []
        self.active = False
        if parent_menu:
            self.depth = parent_menu.depth + 1
        else:
            self.depth = 1
        # alter cached value in main object
        if self.depth > self.main_menu.depth:
            self.main_menu.depth = self.depth

    def set_active(self, active):
        self.active = active
        if self.parent:
            self.parent.set_active(active)

    def populate(self, submenu):
        items = [self]
        for sm in submenu:
            # inherit restrictions from parent
            acl_groups = self.acl_groups.union(sm[2])
            acl_perms = self.acl_perms.union(sm[3])
            m = MenuItem(sm[0], sm[1], acl_groups, acl_perms, self.main_menu, parent_menu = self)
            items += m.populate(sm[4])
            self.submenu.append(m)
        return items

    def hidden(self):
        # return False if field should be displayed to user
        if self.acl_groups and not self.main_menu.user.is_superuser:
            if not self.acl_groups.intersection(self.main_menu.acl_groups):
                return True
        if self.acl_perms and not self.main_menu.user.is_superuser:
            for p in self.acl_perms:
                if p not in self.main_menu.acl_perms:
                    self.main_menu.acl_perms[p] = self.main_menu.user.has_perm(p)
                if not self.main_menu.acl_perms[p]:
                    return True
        return False

    def __unicode__(self):
        if self.hidden():
            return u''
        if self.active:
            style = u'class="%s"' % self.main_menu.css_active_class
        else:
            style = u''
        if self.url:
            s = u'<a href="%s" %s>%s</a>' % (self.url, style, self.title)
        else:
            s = self.title
        if self.active:
            s += ' + '
        if self.submenu:
            s += u'<ul>%s</ul>' % u''.join([unicode(x) for x in self.submenu])
        return u'<li>%s</li>' % s

    def __repr__(self):
        return '<MenuItem>: %s (%s)' % (self.title, self.url)

class Menu(object):
    def __init__(self, menu_config):
        self._items = []
        self.menuitems = []
        self.active = None
        self.acl_groups = set() # all users groups
        self.acl_perms = {} # cached perms (bools)
        self.user = None
        self.path = ''
        self.depth = 0
        for m in menu_config.menu:
            item = MenuItem(m[0], m[1], m[2], m[3], self)
            self.menuitems += item.populate(m[4])
            self._items.append(item)
        self.menuitems.reverse()
        self.css_active_class = getattr(menu_config, 'css_active_class', '')

    @property
    def items(self):
        return [x for x in self._items if not x.hidden()]

    def find_active_menu(self):
        matches = [m for m in self.menuitems if not m.hidden() and m.url and self.path.startswith(m.url)]
        if matches:
            # find the longest menu match
            found = max(matches, key = lambda x: len(x.url))
            if self.active:
                self.active.set_active(False)
            found.set_active(True)
            self.active = found
            return found

        return None

    def set_active_css_class(self, style):
        self.css_active_class = style

    # template utils
    def first_item(self):
        try:
            return self.items[0]
        except IndexError:
            return None

    def last_item(self):
        try:
            return self.items[-1]
        except IndexError:
            return None

    def inner_items(self):
        return self.items[1:-1]

    def __getattr__(self, attr):
        # get specified submenu level in active menu
        if attr.startswith('level'):
            try:
                level = int(attr[5:])
            except ValueError:
                raise AttributeError
            if level not in range(1, self.depth):
                raise AttributeError
            if not self.active or self.active.depth < level:
                return None
            m = self.active
            while m.depth != level:
                m = m.parent
            return m

    def __unicode__(self):
        "return printable <ul> list"
        m = u'<ul>%s</ul>' % ''.join([unicode(x) for x in self.items])
        return '"%s" "%s" %s' % (self.path, self.user, m)

    def __call__(self, request):
        self.user = request.user
        self.path = request.get_full_path()
        self.acl_groups = set([x.name for x in request.user.groups.all().only('name')])
        self.acl_perms = {}
        return self


# load menu configuration from project
from django.conf import settings
menu_config = __import__(settings.ROOT_MENUCONF, {}, {}, [""])
menu = Menu(menu_config)
