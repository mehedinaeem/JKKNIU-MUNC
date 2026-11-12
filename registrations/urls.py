from django.urls import path
from . import views

app_name = 'registrations'
urlpatterns = [
    path('forms/<slug:slug>/submit/', views.PublicFormSubmit.as_view(), name='submit'),
    path('admin/forms/<int:pk>/sheet/', views.FormSubmissionSheet.as_view(), name='form-sheet'),
    path('submission-files/<int:pk>/preview/', views.PrivateImagePreview.as_view(), name='image-preview'),
    path('admin/review/forms/', views.ReviewFormList.as_view(), name='review-forms'),
    path('admin/dashboard/', views.ReviewDashboard.as_view(), name='dashboard'),
    path('admin/submissions/export/', views.SubmissionExport.as_view(), name='export'),
    path('admin/submissions/<uuid:pk>/notes/', views.SubmissionNotes.as_view(), name='notes'),
    path('admin/submissions/', views.SubmissionList.as_view(), name='list'),
    path('admin/submissions/<uuid:pk>/', views.SubmissionDetail.as_view(), name='detail'),
    path('admin/submissions/<uuid:pk>/status/', views.SubmissionStatus.as_view(), name='status'),
]
