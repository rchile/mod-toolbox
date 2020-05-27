import arrow
import markdown as md
from django import template

register = template.Library()


@register.filter
def format_date(value):
    m = arrow.get(value)
    return m.format('YYYY-MM-DD HH:mm:ss')


@register.filter
def human_date(value):
    m = arrow.get(value)
    return m.humanize()


@register.filter
def markdown(value):
    return md.markdown(value)
