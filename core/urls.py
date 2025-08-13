from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('settings/', views.settings_view, name='settings'),

    # API endpoints
    path('api/translate/', views.translate_text, name='translate_text'),
    path('api/analyze/', views.analyze_word, name='analyze_word'),
    path('api/stream-translate/', views.stream_translation, name='stream_translation'),
    path('api/stream-analyze/', views.stream_word_analysis, name='stream_word_analysis'),

    # API Configuration CRUD
    path('api/configs/', views.APIConfigurationView.as_view(), name='api_configs_list'),
    path('api/configs/<int:config_id>/', views.APIConfigurationView.as_view(), name='api_configs_detail'),

    # Prompt Template CRUD
    path('api/templates/', views.PromptTemplateView.as_view(), name='prompt_templates_list'),
    path('api/templates/<int:template_id>/', views.PromptTemplateView.as_view(), name='prompt_templates_detail'),
]
