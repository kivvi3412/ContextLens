import json

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import APIConfiguration, PromptTemplate, AnalysisConfiguration
from .openai_service import get_active_templates, create_openai_service


def index(request):
    """Main page view"""
    return render(request, 'core/index.html')


def settings_view(request):
    """Settings page view"""
    api_configs = APIConfiguration.objects.all()
    translation_templates = PromptTemplate.objects.filter(template_type='translation')
    analysis_templates = PromptTemplate.objects.filter(template_type='word_analysis')
    sentence_templates = PromptTemplate.objects.filter(template_type='sentence_analysis')
    analysis_config = AnalysisConfiguration.get_current()

    context = {
        'api_configs': api_configs,
        'translation_templates': translation_templates,
        'analysis_templates': analysis_templates,
        'sentence_templates': sentence_templates,
        'analysis_config': analysis_config,
    }
    return render(request, 'core/settings.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def translate_text(request):
    """API endpoint for full text translation"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')

        templates = get_active_templates()
        if 'translation' not in templates:
            return JsonResponse({'error': 'No active translation template found'}, status=400)

        template = templates['translation']
        service = create_openai_service(template)

        result = service.get_translation_sync(template, text)

        return JsonResponse({
            'translation': result,
            'status': 'success'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def analyze_word(request):
    """API endpoint for word/phrase analysis"""
    try:
        data = json.loads(request.body)
        all_text = data.get('all_text', '')
        selected_text = data.get('selected_text', '')

        templates = get_active_templates()
        if 'word_analysis' not in templates:
            return JsonResponse({'error': 'No active word analysis template found'}, status=400)

        template = templates['word_analysis']
        service = create_openai_service(template)

        result = service.get_word_analysis_sync(template, all_text, selected_text)

        return JsonResponse({
            'analysis': result,
            'status': 'success'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def stream_translation(request):
    """Streaming API endpoint for translation"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        text = data.get('text', '')

        if not text.strip():
            return JsonResponse({'error': 'No text provided'}, status=400)

        templates = get_active_templates()
        if 'translation' not in templates:
            return JsonResponse({'error': 'No active translation template found. Please configure API settings first.'},
                                status=400)

        template = templates['translation']

        # Note: API key check is now handled in the service layer to allow demo mode
        service = create_openai_service(template)

        def generate_stream():
            try:
                chunk_count = 0
                for chunk in service.stream_translation_sync(template, text):
                    chunk_count += 1
                    
                    # Debug log
                    print(f"Django view received chunk: {repr(chunk)}")
                    
                    # Check if this is thinking content
                    if chunk.startswith('__THINKING__:'):
                        thinking_text = chunk[13:]  # Remove __THINKING__: prefix
                        print(f"Django view sending thinking: {thinking_text}")
                        yield f"data: {json.dumps({'content': thinking_text, 'type': 'thinking'})}\n\n"
                    elif chunk == '__THINKING_DONE__':
                        print("Django view sending thinking done")
                        yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'content': chunk, 'type': 'content'})}\n\n"

                if chunk_count == 0:
                    yield f"data: {json.dumps({'content': 'No response received from API. Check your API key and model settings.', 'type': 'error'})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'content': f'Stream error: {str(e)}', 'type': 'error'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def stream_word_analysis(request):
    """Streaming API endpoint for word analysis"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        all_text = data.get('all_text', '')
        selected_text = data.get('selected_text', '')

        if not all_text.strip() or not selected_text.strip():
            return JsonResponse({'error': 'No text or selection provided'}, status=400)

        templates = get_active_templates()
        analysis_config = AnalysisConfiguration.get_current()
        selected_words = len(selected_text.split())
        
        # 使用配置的阈值判断是句子还是词汇/短语
        if selected_words > analysis_config.word_group_threshold:
            # 句子分析
            if 'sentence_analysis' not in templates:
                return JsonResponse(
                    {'error': 'No active sentence analysis template found. Please configure API settings first.'}, status=400)
            template = templates['sentence_analysis']
        else:
            # 单词/短语分析 
            if 'word_analysis' not in templates:
                return JsonResponse(
                    {'error': 'No active word analysis template found. Please configure API settings first.'}, status=400)
            template = templates['word_analysis']

        # Note: API key check is now handled in the service layer to allow demo mode
        service = create_openai_service(template)

        def generate_stream():
            try:
                chunk_count = 0
                for chunk in service.stream_word_analysis_sync(template, all_text, selected_text, selected_words > analysis_config.word_group_threshold):
                    chunk_count += 1
                    
                    # Debug log
                    # print(f"Django analysis view received chunk: {repr(chunk)}")
                    
                    # Check if this is thinking content
                    if chunk.startswith('__THINKING__:'):
                        thinking_text = chunk[13:]  # Remove __THINKING__: prefix
                        # print(f"Django analysis view sending thinking: {thinking_text}")
                        yield f"data: {json.dumps({'content': thinking_text, 'type': 'thinking'})}\n\n"
                    elif chunk == '__THINKING_DONE__':
                        print("Django analysis view sending thinking done")
                        yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'content': chunk, 'type': 'content'})}\n\n"

                if chunk_count == 0:
                    yield f"data: {json.dumps({'content': 'No response received from API. Check your API key and model settings.', 'type': 'error'})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'content': f'Stream error: {str(e)}', 'type': 'error'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class APIConfigurationView(View):
    """CRUD operations for API configurations"""

    def get(self, request, config_id=None):
        if config_id:
            config = get_object_or_404(APIConfiguration, id=config_id)
            return JsonResponse({
                'id': config.id,
                'name': config.name,
                'base_url': config.base_url,
                'model_name': config.model_name,
                'has_api_key': bool(config.api_key and config.api_key.strip()),
            })
        else:
            configs = APIConfiguration.objects.all().values('id', 'name', 'base_url', 'model_name')
            return JsonResponse({'configs': list(configs)})

    def post(self, request):
        try:
            data = json.loads(request.body)
            config = APIConfiguration.objects.create(
                name=data['name'],
                api_key=data['api_key'],
                base_url=data.get('base_url', 'https://api.openai.com/v1'),
                model_name=data.get('model_name', 'gpt-4')
            )
            return JsonResponse({
                'id': config.id,
                'status': 'success',
                'message': 'API configuration created successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def put(self, request, config_id):
        try:
            config = get_object_or_404(APIConfiguration, id=config_id)
            data = json.loads(request.body)

            config.name = data.get('name', config.name)
            # Only update API key if a new one is provided
            if 'api_key' in data and data['api_key'].strip():
                config.api_key = data['api_key']
            config.base_url = data.get('base_url', config.base_url)
            config.model_name = data.get('model_name', config.model_name)
            config.save()

            return JsonResponse({
                'status': 'success',
                'message': 'API configuration updated successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def delete(self, request, config_id):
        try:
            config = get_object_or_404(APIConfiguration, id=config_id)
            config.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'API configuration deleted successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class PromptTemplateView(View):
    """CRUD operations for prompt templates"""

    def get(self, request, template_id=None):
        if template_id:
            template = get_object_or_404(PromptTemplate, id=template_id)
            return JsonResponse({
                'id': template.id,
                'name': template.name,
                'template_type': template.template_type,
                'prompt_text': template.prompt_text,
                'api_config_id': template.api_config.id,
                'reasoning_effort': template.reasoning_effort,
                'is_active': template.is_active,
            })
        else:
            templates = PromptTemplate.objects.all().values(
                'id', 'name', 'template_type', 'prompt_text',
                'api_config__name', 'reasoning_effort', 'is_active'
            )
            return JsonResponse({'templates': list(templates)})

    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['name', 'template_type', 'prompt_text', 'api_config_id']
            for field in required_fields:
                if field not in data or not data[field]:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
            
            api_config = get_object_or_404(APIConfiguration, id=data['api_config_id'])

            # Validate template_type
            valid_types = [choice[0] for choice in PromptTemplate.TEMPLATE_TYPES]
            if data['template_type'] not in valid_types:
                return JsonResponse({'error': f'Invalid template_type. Must be one of: {valid_types}'}, status=400)

            # Deactivate other templates of the same type if this is active
            if data.get('is_active', False):
                PromptTemplate.objects.filter(
                    template_type=data['template_type'],
                    is_active=True
                ).update(is_active=False)

            template = PromptTemplate.objects.create(
                name=data['name'],
                template_type=data['template_type'],
                prompt_text=data['prompt_text'],
                api_config=api_config,
                reasoning_effort=data.get('reasoning_effort', 'low'),
                is_active=data.get('is_active', False)
            )

            return JsonResponse({
                'id': template.id,
                'status': 'success',
                'message': 'Prompt template created successfully'
            })
        except KeyError as e:
            return JsonResponse({'error': f'Missing required field: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def put(self, request, template_id):
        try:
            template = get_object_or_404(PromptTemplate, id=template_id)
            data = json.loads(request.body)

            # Deactivate other templates of the same type if this is being activated
            if data.get('is_active', False) and not template.is_active:
                PromptTemplate.objects.filter(
                    template_type=template.template_type,
                    is_active=True
                ).update(is_active=False)

            template.name = data.get('name', template.name)
            template.prompt_text = data.get('prompt_text', template.prompt_text)
            template.reasoning_effort = data.get('reasoning_effort', template.reasoning_effort)
            template.is_active = data.get('is_active', template.is_active)

            if 'api_config_id' in data:
                template.api_config = get_object_or_404(APIConfiguration, id=data['api_config_id'])

            template.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Prompt template updated successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def delete(self, request, template_id):
        try:
            template = get_object_or_404(PromptTemplate, id=template_id)
            template.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Prompt template deleted successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AnalysisConfigurationView(View):
    """CRUD operations for analysis configuration"""

    def get(self, request):
        config = AnalysisConfiguration.get_current()
        return JsonResponse({
            'id': config.id,
            'word_group_threshold': config.word_group_threshold,
            'sentence_threshold': config.sentence_threshold,
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
            config = AnalysisConfiguration.get_current()
            
            config.word_group_threshold = data.get('word_group_threshold', config.word_group_threshold)
            config.sentence_threshold = data.get('sentence_threshold', config.sentence_threshold)
            config.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Analysis configuration updated successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
