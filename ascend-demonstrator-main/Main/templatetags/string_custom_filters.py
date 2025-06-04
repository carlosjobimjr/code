from django import template
import re

register = template.Library()

@register.filter(name='to_id')
def to_id(value):
    """Convert a string to a valid HTML id."""
    # Replace any non-alphanumeric character with underscore
    return re.sub(r'[^a-zA-Z0-9]', '_', value)