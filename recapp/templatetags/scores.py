from django import template
from django.utils.safestring import mark_safe

from recapp.models import Run

register = template.Library()


@register.filter(name='score')
def score(time):
    return f"{time//60000:02}:{time//1000%60:02}.{time%1000:03}"


@register.filter(name='run_time')
def run_time(run: Run):
    if run.error is not None or run.score is None:
        return mark_safe("Errored")
    if not run.score.success:
        return mark_safe("Failed")

    formatted = score(run.score.score_time)

    if run.score.is_desync:
        return mark_safe(f"<span class=\"desync\">{formatted}</span>")
    else:
        return mark_safe(f"{formatted}")
