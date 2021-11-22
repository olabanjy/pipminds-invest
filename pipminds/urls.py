
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include 
from investment.views import error404, error500
from django.contrib.auth.decorators import login_required

 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('home.urls', namespace='home')),
    path('u/', include('users.urls', namespace='users')),
    path('wallet/', include('wallet.urls', namespace='wallet')),
    path('investment/', include('investment.urls', namespace='investment')),
    path('pools/', include('pools.urls', namespace='pools')),


]


handler404 = error404
handler500 = error500




if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL,
                      document_root=settings.STATIC_ROOT)