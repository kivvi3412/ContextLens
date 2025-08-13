from django.core.management.base import BaseCommand

from core.models import APIConfiguration, PromptTemplate


class Command(BaseCommand):
    help = 'Create default API configurations and prompt templates'

    def handle(self, *args, **options):
        # Create default API configuration
        api_config, created = APIConfiguration.objects.get_or_create(
            name="Default OpenAI",
            defaults={
                'api_key': 'your-api-key-here',
                'base_url': 'https://api.openai.com/v1',
                'model_name': 'gpt-4'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created default API configuration'))

        # Create default translation template
        translation_template, created = PromptTemplate.objects.get_or_create(
            name="Default Translation",
            template_type="translation",
            defaults={
                'prompt_text': """Please provide a high-quality, accurate translation of the following English text to Chinese. Focus on capturing both the literal meaning and the cultural context. Ensure the translation is natural and fluent in Chinese.

Text to translate:
{all_input}

Please provide only the Chinese translation without any explanations or additional text.""",
                'api_config': api_config,
                'reasoning_effort': 'medium',
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created default translation template'))

        # Create default word analysis template
        analysis_template, created = PromptTemplate.objects.get_or_create(
            name="Default Word Analysis",
            template_type="word_analysis",
            defaults={
                'prompt_text': """用户输入的是 {input_select} ，翻译单词或者短语在当前句子中的意思，根据以下规范:

输出词语短语 input_select 提供音标（IPA） **常见含义**：列出2-3个最常见的定义
输出这个单词在文中的句子，句子翻译
在上下文中这个单词的意思，以下是输出例子严格按照这个例子的格式输出(包括加粗，换行)


-  **distributions** /distrɪ'beɪʃənz/ 
   -  n. 版本, 发行版; 分配, 分发
       ...如果有更多词性和意思写在这里如果没有不要输出...
   -  There are many Linux distributions available. 
      有许许多多的Linux发行版可供选择。

全文文本: {all_input}""",
                'api_config': api_config,
                'reasoning_effort': 'low',
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created default word analysis template'))

        # Create default sentence analysis template
        sentence_template, created = PromptTemplate.objects.get_or_create(
            name="Default Sentence Analysis",
            template_type="sentence_analysis",
            defaults={
                'prompt_text': """{input_select} 根据上下文翻译这句话的中文意思，根据以下规范:

中文译文**，切勿泄漏任何中间思考或解释步骤。

步骤（仅在内部思考，不得输出）  

>  1. 对原文做句法与成分分析：识别主句、从句、并列/修饰关系、插入语及引述等，并纠正潜在断句或标点错误。  
>  2. 根据分析结果重建清晰的逻辑结构。  
>  3. 在保持信息完整的前提下，用符合现代书面中文习惯的自然表达完成翻译；必要时调整语序、增补隐含逻辑词，使句意准确流畅。  
>  4. 确保用词正式、精炼，语气与原文一致；避免逐词直译导致的生硬。  
>
>  输出要求  
>
>  - 仅输出**最终译文**一行，不附加步骤、注释、序号或空行。  

全文文本: {all_input}""",
                'api_config': api_config,
                'reasoning_effort': 'high',
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created default sentence analysis template'))

        # Create GPT-5 example templates
        gpt5_config, created = APIConfiguration.objects.get_or_create(
            name="GPT-5 High Reasoning",
            defaults={
                'api_key': 'your-gpt5-api-key-here',
                'base_url': 'https://api.openai.com/v1',
                'model_name': 'gpt-5'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created GPT-5 API configuration'))

        # Advanced translation template with GPT-5
        advanced_translation, created = PromptTemplate.objects.get_or_create(
            name="Advanced Translation (GPT-5)",
            template_type="translation",
            defaults={
                'prompt_text': """You are an expert translator specializing in English to Chinese translation. Please provide a high-quality, nuanced translation that:

1. Preserves the original meaning and tone
2. Adapts cultural references appropriately for Chinese readers
3. Uses natural, contemporary Chinese expressions
4. Maintains the style and register of the original text

Consider the context, audience, and purpose of the text when translating.

**Text to translate:**
{all_input}

Provide only the Chinese translation. Be precise, natural, and culturally appropriate.""",
                'api_config': gpt5_config,
                'reasoning_effort': 'high',
                'is_active': False
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created advanced GPT-5 translation template'))

        self.stdout.write(
            self.style.SUCCESS(
                '\nDefault setup complete! '
                'Don\'t forget to update your API keys in the settings page.'
            )
        )
