"""
@summary: Menu for Django HttpRequest object
@requires: in settings.py:\n
           kobo.django.menu.context_processors.menu_context_processor in TEMPLATE_CONTEXT_PROCESSORS,\n
           kobo.django.menu.middleware.MenuMiddleware in MIDDLEWARE_CLASSES\n

@note: to specify a menu item, create file menu.py in you apps with following format:\n
       url = url_to_app (view url/view name)\n
       label = menu_item_label\n
       order = menu_item_order\n
       submenu = [{'url':sub_item_url, 'label':sub_item_label},...]
"""
