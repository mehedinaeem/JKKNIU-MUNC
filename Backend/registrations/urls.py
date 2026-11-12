from django.urls import path
from . import views

app_name = 'registrations'
urlpatterns = [
    path('forms/<slug:slug>/submit/', views.PublicFormSubmit.as_view(), name='submit'),
    path('admin/submissions/', views.SubmissionList.as_view(), name='list'),
    path('admin/submissions/<uuid:pk>/', views.SubmissionDetail.as_view(), name='detail'),
    path('admin/submissions/<uuid:pk>/status/', views.SubmissionStatus.as_view(), name='status'),
]
