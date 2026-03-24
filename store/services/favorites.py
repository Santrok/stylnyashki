from ..models import Favorite


def ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_favorite(request):
    if request.user.is_authenticated:
        fav, _ = Favorite.objects.get_or_create(user=request.user)
        return fav

    session_key = ensure_session_key(request)
    fav, _ = Favorite.objects.get_or_create(user=None, session_key=session_key)
    return fav