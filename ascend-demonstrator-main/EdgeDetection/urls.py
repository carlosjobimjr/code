from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
app_name = 'edge_detection'
urlpatterns = [
    path('<int:id>/', views.edge_detection, name='edge_detection'),
    path('upload/file/', views.file_upload_view, name='file_upload'),
    path('upload/image/', views.image_upload_view, name='image_upload'),
    path('run/', views.run_edge_detection, name='run_edge_detection'),
    path('process/', views.edge_detection, name='edge_detection_view'),
    path('process_dxf/', views.process_dxf, name='process_dxf'),
]