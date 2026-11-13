from django.urls import path
from . import views
from .webhooks import BrevoWebhook, Unsubscribe

app_name = 'mailing'
urlpatterns = [
    path('admin/email/overview/', views.Overview.as_view()),
    path('admin/email/configuration/', views.Configuration.as_view()),
    path('admin/email/templates/', views.TemplateList.as_view()),
    path('admin/email/templates/preview/', views.TemplatePreview.as_view()),
    path('admin/email/templates/<int:pk>/', views.TemplateDetail.as_view()),
    path('admin/email/campaigns/', views.CampaignList.as_view()),
    path('admin/email/campaigns/<int:pk>/', views.CampaignDetail.as_view()),
    path('admin/email/campaigns/<int:pk>/<str:action>/', views.CampaignAction.as_view()),
    path('admin/email/recipients/', views.RecipientCount.as_view()),
    path('admin/email/recipient-options/', views.RecipientOptions.as_view()),
    path('admin/email/messages/', views.MessageList.as_view()),
    path('admin/email/messages/<uuid:pk>/<str:action>/', views.MessageAction.as_view()),
    path('admin/email/settings/<int:pk>/', views.EventSettings.as_view()),
    path('admin/email/preferences/', views.PreferenceUpdate.as_view()),
    path('admin/email/submissions/<uuid:pk>/', views.SubmissionMail.as_view()),
    path('admin/email/payments/<uuid:pk>/', views.VerifyPayment.as_view()),
    path('webhooks/brevo/', BrevoWebhook.as_view()),
    path('email/unsubscribe/', Unsubscribe.as_view()),
]
