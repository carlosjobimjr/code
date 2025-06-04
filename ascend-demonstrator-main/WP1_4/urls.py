from django.contrib import admin
from django.urls import path, include
from Login import views as v
from EnergyCapture.views import oauth_callback  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Main.urls')),
    path('', include('MainData.urls')),
    path('', include('Dashboard.urls')),
    path('', include('Export.urls')),
    path('', include('Admin.urls')),
    path('', include('Login.urls')),
    path('', include('EnergyCapture.urls')),
    path("EnergyCapture/", include("EnergyCapture.urls")),
    path('', include('django.contrib.auth.urls')),
    path('faq/', v.faq, name='faq'),
    path('edge_detection/', include('EdgeDetection.urls')),
    path('oauth/callback/', oauth_callback, name='oauth_callback'),  
]
