from typing import Dict, Generator

from openai import OpenAI, AsyncOpenAI

from .models import APIConfiguration, PromptTemplate


class OpenAIService:
    def __init__(self, api_config: APIConfiguration):
        self.config = api_config
        # Use synchronous client for Django sync views
        self.client = OpenAI(
            api_key=api_config.api_key,
            base_url=api_config.base_url
        )
        # Keep async client for future use
        self.async_client = AsyncOpenAI(
            api_key=api_config.api_key,
            base_url=api_config.base_url
        )

    def _is_reasoning_model(self, model_name: str) -> bool:
        """Check if the model is a reasoning model that requires responses API"""
        reasoning_prefixes = ('o1', 'o3', 'o4', 'gpt-5')
        return any(model_name.startswith(prefix) for prefix in reasoning_prefixes)

    def _prepare_prompt(self, template: PromptTemplate, all_input: str = "", input_select: str = "") -> str:
        """Prepare prompt by substituting placeholders"""
        prompt = template.prompt_text
        prompt = prompt.replace('{all_input}', all_input)
        prompt = prompt.replace('{input_select}', input_select)
        return prompt

    def get_translation_sync(self, template: PromptTemplate, text: str) -> str:
        """Get full text translation synchronously"""
        prompt = self._prepare_prompt(template, all_input=text)

        try:
            response = self.client.chat.completions.create(
                model=template.api_config.model_name,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def get_word_analysis_sync(self, template: PromptTemplate, all_text: str, selected_text: str) -> str:
        """Get word/phrase analysis synchronously"""
        prompt = self._prepare_prompt(template, all_input=all_text, input_select=selected_text)

        try:
            response = self.client.chat.completions.create(
                model=template.api_config.model_name,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def stream_translation_sync(self, template: PromptTemplate, text: str) -> Generator[str, None, None]:
        """Stream translation response synchronously"""
        print(
            f"🚀 Translation Request - Model: {template.api_config.model_name}, Reasoning Effort: {template.reasoning_effort}")
        prompt = self._prepare_prompt(template, all_input=text)

        try:
            # Check if this is a test/demo mode (API key not properly set)
            if not self.config.api_key or self.config.api_key == 'your-api-key-here':
                # Demo mode - simulate streaming response
                demo_response = f"[Demo模式] 输入文本的中文翻译：\\n\\n{text}\\n\\n请在设置中配置您的OpenAI API密钥以获得真实翻译。"
                import time
                for i in range(0, len(demo_response), 5):
                    chunk = demo_response[i:i + 5]
                    yield chunk
                    time.sleep(0.05)  # Simulate network delay
                return

            # Check if this is a reasoning model (o1, o3, o4, gpt-5)
            is_reasoning_model = self._is_reasoning_model(template.api_config.model_name)

            if is_reasoning_model:
                # For reasoning models, use responses API
                try:
                    print(f"Using reasoning model: {template.api_config.model_name}")
                    stream = self.client.responses.create(
                        model=template.api_config.model_name,
                        input=[{
                            "role": "developer",
                            "content": [{
                                "type": "input_text",
                                "text": prompt
                            }]
                        }],
                        text={
                            "format": {"type": "text"},
                            "verbosity": "medium"
                        },
                        reasoning={
                            "effort": template.reasoning_effort or "minimal",
                            "summary": "auto"
                        },
                        tools=[],
                        store=True,
                        stream=True
                    )

                    thinking_content = ""
                    last_reasoning_line = ""
                    
                    for event in stream:
                        # print(f"Translation Event: {type(event).__name__} - {getattr(event, 'type', 'unknown')}")
                        
                        # Handle reasoning summary text delta events
                        if hasattr(event, 'type') and event.type == 'response.reasoning_summary_text.delta':
                            if hasattr(event, 'delta') and event.delta:
                                thinking_content += event.delta
                                # print(f"Translation Thinking delta: {repr(event.delta)}")
                                # Send each delta as thinking content
                                yield f"__THINKING__:{event.delta}"
                        
                        # Handle reasoning summary done events
                        elif hasattr(event, 'type') and event.type == 'response.reasoning_summary_text.done':
                            print("Translation Thinking done, sending reset signal")
                            yield "__THINKING_DONE__"
                                
                        # Handle regular output text delta events  
                        elif hasattr(event, 'type') and event.type == 'response.output_text.delta':
                            if hasattr(event, 'delta') and hasattr(event, 'output_index'):
                                # print(f"Translation Output delta - index: {event.output_index}, delta: {repr(event.delta)}")
                                if event.output_index == 1:  # Final output content only
                                    yield event.delta
                        elif hasattr(event, 'delta') and event.delta:
                            # print(f"Translation Fallback delta: {repr(event.delta)}")
                            # Fallback for events without output_index (likely final output)
                            yield event.delta

                except Exception as responses_error:
                    print(f"Responses API failed: {responses_error}")
                    # Fallback to chat completions
                    response = self.client.chat.completions.create(
                        model=template.api_config.model_name,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    content = response.choices[0].message.content
                    # Simulate streaming
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        yield content[i:i + chunk_size]

            else:
                # For regular models, use standard streaming
                stream = self.client.chat.completions.create(
                    model=template.api_config.model_name,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }],
                    stream=True
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield error_msg

    def stream_word_analysis_sync(self, template: PromptTemplate, all_text: str, selected_text: str, is_sentence: bool = False) -> Generator[
        str, None, None]:
        """Stream word/phrase analysis response synchronously"""
        analysis_type = "Sentence" if is_sentence else "Word/Phrase"
        print(
            f"🔍 {analysis_type} Analysis Request - Model: {template.api_config.model_name}, Reasoning Effort: {template.reasoning_effort}, Selected: '{selected_text}'")
        prompt = self._prepare_prompt(template, all_input=all_text, input_select=selected_text)

        try:
            # Check if this is a test/demo mode (API key not properly set)
            if not self.config.api_key or self.config.api_key == 'your-api-key-here':
                # Demo mode - simulate word analysis
                if is_sentence:
                    demo_response = f"""[Demo模式] 句子分析："{selected_text}"

1. **句子结构**: 主语 + 谓语 + 宾语
2. **语法要点**: 
   - 时态：现在时/过去时/将来时
   - 语态：主动语态/被动语态
   - 句型：陈述句/疑问句/感叹句
3. **重要词汇**:
   - 关键词1：含义解释
   - 关键词2：含义解释
4. **翻译**: {selected_text}的中文翻译
5. **语境含义**: 在当前文章中，这句话表示...

请在设置中配置您的OpenAI API密钥以获得详细的句子分析。"""
                else:
                    demo_response = f"""[Demo模式] 词汇分析："{selected_text}"

1. **单词/短语**: {selected_text}
2. **音标**: 请配置API密钥获取准确发音
3. **词性**: 名词/动词/形容词等
4. **常见含义**: 
   - 含义1：示例定义
   - 含义2：示例定义
5. **例句**: 
   - Example sentence 1
   - Example sentence 2
6. **语境含义**: 在当前文章中，该词表示...

请在设置中配置您的OpenAI API密钥以获得详细的词汇分析。"""
                import time
                for i in range(0, len(demo_response), 8):
                    chunk = demo_response[i:i + 8]
                    yield chunk
                    time.sleep(0.03)
                return

            # Check if this is a reasoning model (o1, o3, o4, gpt-5)
            is_reasoning_model = self._is_reasoning_model(template.api_config.model_name)

            if is_reasoning_model:
                # For reasoning models, use responses API
                try:
                    print(f"Using reasoning model for analysis: {template.api_config.model_name}")
                    stream = self.client.responses.create(
                        model=template.api_config.model_name,
                        input=[{
                            "role": "developer",
                            "content": [{
                                "type": "input_text",
                                "text": prompt
                            }]
                        }],
                        text={
                            "format": {"type": "text"},
                            "verbosity": "medium"
                        },
                        reasoning={
                            "effort": template.reasoning_effort or "minimal",
                            "summary": "auto"
                        },
                        tools=[],
                        store=True,
                        stream=True
                    )

                    thinking_content = ""
                    last_reasoning_line = ""
                    
                    for event in stream:
                        # print(f"Analysis Event: {type(event).__name__} - {getattr(event, 'type', 'unknown')}")
                        
                        # Handle reasoning summary text delta events
                        if hasattr(event, 'type') and event.type == 'response.reasoning_summary_text.delta':
                            if hasattr(event, 'delta') and event.delta:
                                thinking_content += event.delta
                                # print(f"Analysis Thinking delta: {repr(event.delta)}")
                                # Send each delta as thinking content
                                yield f"__THINKING__:{event.delta}"
                        
                        # Handle reasoning summary done events
                        elif hasattr(event, 'type') and event.type == 'response.reasoning_summary_text.done':
                            print("Analysis Thinking done, sending reset signal")
                            yield "__THINKING_DONE__"
                                
                        # Handle regular output text delta events
                        elif hasattr(event, 'type') and event.type == 'response.output_text.delta':
                            if hasattr(event, 'delta') and hasattr(event, 'output_index'):
                                # print(f"Analysis Output delta - index: {event.output_index}, delta: {repr(event.delta)}")
                                if event.output_index == 1:  # Final output content only
                                    yield event.delta
                        elif hasattr(event, 'delta') and event.delta:
                            # print(f"Analysis Fallback delta: {repr(event.delta)}")
                            # Fallback for events without output_index (likely final output)
                            yield event.delta

                except Exception as responses_error:
                    print(f"Responses API failed: {responses_error}")
                    # Fallback to chat completions
                    response = self.client.chat.completions.create(
                        model=template.api_config.model_name,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    content = response.choices[0].message.content
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        yield content[i:i + chunk_size]

            else:
                # For regular models, use standard streaming
                stream = self.client.chat.completions.create(
                    model=template.api_config.model_name,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }],
                    stream=True
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield error_msg

    # Keep async methods for future use
    async def get_translation(self, template: PromptTemplate, text: str) -> str:
        """Get full text translation"""
        prompt = self._prepare_prompt(template, all_input=text)

        try:
            is_reasoning_model = self._is_reasoning_model(template.api_config.model_name)

            if is_reasoning_model:
                # For reasoning models, use responses API
                response = await self.async_client.responses.create(
                    model=template.api_config.model_name,
                    input=[{
                        "role": "developer",
                        "content": [{
                            "type": "input_text",
                            "text": prompt
                        }]
                    }],
                    text={
                        "format": {
                            "type": "text"
                        },
                        "verbosity": "medium"
                    },
                    reasoning={
                        "effort": template.reasoning_effort or "minimal",
                        "summary": "auto"
                    },
                    tools=[],
                    store=True,
                    stream=False
                )
                return response.text.value
            else:
                response = await self.async_client.chat.completions.create(
                    model=template.api_config.model_name,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    async def get_word_analysis(self, template: PromptTemplate, all_text: str, selected_text: str) -> str:
        """Get word/phrase analysis"""
        prompt = self._prepare_prompt(template, all_input=all_text, input_select=selected_text)

        try:
            is_reasoning_model = self._is_reasoning_model(template.api_config.model_name)

            if is_reasoning_model:
                # For reasoning models, use responses API
                response = await self.async_client.responses.create(
                    model=template.api_config.model_name,
                    input=[{
                        "role": "developer",
                        "content": [{
                            "type": "input_text",
                            "text": prompt
                        }]
                    }],
                    text={
                        "format": {
                            "type": "text"
                        },
                        "verbosity": "medium"
                    },
                    reasoning={
                        "effort": template.reasoning_effort or "minimal",
                        "summary": "auto"
                    },
                    tools=[],
                    store=True,
                    stream=False
                )
                return response.text.value
            else:
                response = await self.async_client.chat.completions.create(
                    model=template.api_config.model_name,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"


def get_active_templates() -> Dict[str, PromptTemplate]:
    """Get currently active templates for translation, word analysis, and sentence analysis"""
    templates = {}
    try:
        translation_template = PromptTemplate.objects.filter(
            template_type='translation',
            is_active=True
        ).first()
        if translation_template:
            templates['translation'] = translation_template

        analysis_template = PromptTemplate.objects.filter(
            template_type='word_analysis',
            is_active=True
        ).first()
        if analysis_template:
            templates['word_analysis'] = analysis_template
            
        sentence_template = PromptTemplate.objects.filter(
            template_type='sentence_analysis',
            is_active=True
        ).first()
        if sentence_template:
            templates['sentence_analysis'] = sentence_template

    except Exception:
        pass

    return templates


def create_openai_service(template: PromptTemplate) -> OpenAIService:
    """Create OpenAI service instance from template"""
    return OpenAIService(template.api_config)
