from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def qs(context, **kwargs):
    """
    Создает строку запроса на основе текущего запроса. GET с обновлениями.

    Использование:
        {% qs Category=c.slug page=None %}
        — если значение равно None => удалить параметр
        — если значение равно списку/кортежу => установить список
    """
    request = context.get("request")
    if request is None:
        return ""

    qd = request.GET.copy()

    for key, value in kwargs.items():
        if value is None:
            qd.pop(key, None)
            continue

        if isinstance(value, (list, tuple)):
            qd.setlist(key, [str(v) for v in value])
        else:
            qd[key] = str(value)

    s = qd.urlencode()
    return f"?{s}" if s else ""