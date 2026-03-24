def _build_pagination_pages(page_obj, window=2):
    """
    Возвращает список элементов для пагинации.
    Числа = номера страниц, None = троеточие.
    """
    total = page_obj.paginator.num_pages
    current = page_obj.number

    if total <= 1:
        return []

    pages = {1, total}
    for p in range(current - window, current + window + 1):
        if 1 <= p <= total:
            pages.add(p)

    pages = sorted(pages)

    result = []
    prev = None
    for p in pages:
        if prev is not None and p - prev > 1:
            result.append(None)  # "..."
        result.append(p)
        prev = p
    return result