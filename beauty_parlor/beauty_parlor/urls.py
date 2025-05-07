from django.conf.urls import handler400, handler403, handler404, handler500
from beauty_app.views.error_views import bad_request, permission_denied, page_not_found, server_error
from django.contrib import admin
from django.urls import path,include



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('beauty_app.urls')),
]







handler400 = 'beauty_app.views.error_views.bad_request'
handler403 = 'beauty_app.views.error_views.permission_denied'
handler404 = 'beauty_app.views.error_views.page_not_found'
handler500 = 'beauty_app.views.error_views.server_error'
