def call_if_callable(obj):
    """
    Determines if an object is callable, and returns its value or value of its call. 
    """
    if callable(obj):
        return obj()
    else:
        return obj
