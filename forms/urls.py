from django.urls import path
from . import views
from registrations.views import PrivateFileDownload

app_name = 'forms'
urlpatterns = [
    path('events/<slug:event_slug>/forms/', views.EventFormList.as_view(), name='event-forms'),
    path('forms/<slug:form_slug>/', views.PublicFormDetail.as_view(), name='detail'),
    path('forms/<slug:form_slug>/submissions/', views.FormSubmit.as_view(), name='submit'),
    path('admin/forms/', views.StaffFormCreate.as_view(), name='create'),
    path('admin/forms/<int:pk>/', views.StaffFormDetail.as_view(), name='edit'),
    path('admin/forms/<int:pk>/preview/', views.StaffFormPreview.as_view(), name='preview'),
    path('admin/forms/<int:pk>/publish/', views.StaffFormPublish.as_view(), name='publish'),
    path('admin/forms/<int:pk>/duplicate/', views.StaffFormDuplicate.as_view(), name='duplicate'),
    path('submission-files/<int:pk>/', PrivateFileDownload.as_view(), name='file-download'),
]
