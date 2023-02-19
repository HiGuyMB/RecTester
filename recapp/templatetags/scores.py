from django import template

register = template.Library()


@register.filter(name='score')
def score(time):
	return f"{time//60000:02}:{time//1000%60:02}.{time%1000:03}"


