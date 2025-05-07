

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

@require_POST
@csrf_protect
def keep_session_alive(request):
    if request.user.is_authenticated:
        request.session.modified = True
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=401)