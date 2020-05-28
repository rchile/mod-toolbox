import arrow
import markdown as md
from django import template

from system.constants import MOD_ACTIONS

register = template.Library()


@register.filter
def format_date(value):
    m = arrow.get(value)
    return m.format('YYYY-MM-DD HH:mm:ss')


@register.filter
def human_date(value):
    m = arrow.get(value)
    return m.humanize().rstrip(' ago')


@register.filter
def markdown(value):
    return md.markdown(value)


@register.filter
def modaction_description(value):
    return MOD_ACTIONS.get(value, value)
