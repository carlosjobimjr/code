from django import template
register = template.Library()
from Main.views import SubProcessHandler

def get_handler_params():
    subprocess_handler = SubProcessHandler()
    handler_info = subprocess_handler.handlers.get('Heat Mould and Platten Up')
    return handler_info[1] if handler_info else {}

@register.simple_tag
def get_temp1():
    params = get_handler_params()
    return params.get('temp1',341)

@register.simple_tag
def get_upper_bound():
    params = get_handler_params()
    temp1 = params.get('temp1', 341)
    return temp1 + 5

@register.simple_tag
def get_lower_bound():
    params = get_handler_params()
    temp1 = params.get('temp1', 341)
    return temp1 - 5

@register.simple_tag
def get_tolerance():
    return 5

@register.filter
def sub(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return None