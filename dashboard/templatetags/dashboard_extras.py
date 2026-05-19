from django import template

register = template.Library()


@register.filter
def dot_to_space(value):
    """Format usernames like 'first.last' as 'first last' for display."""
    if value is None:
        return ""
    return str(value).replace('.', ' ')
