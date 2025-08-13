from django.db import models


class APIConfiguration(models.Model):
    name = models.CharField(max_length=100, unique=True)
    api_key = models.CharField(max_length=500)
    base_url = models.URLField(default='https://api.openai.com/v1')
    model_name = models.CharField(max_length=100, default='gpt-4')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.model_name}"


class PromptTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('translation', 'Full Text Translation'),
        ('word_analysis', 'Word/Phrase Analysis'),
        ('sentence_analysis', 'Sentence Analysis'),
    ]

    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    prompt_text = models.TextField()
    api_config = models.ForeignKey(APIConfiguration, on_delete=models.CASCADE)
    reasoning_effort = models.CharField(
        max_length=10,
        choices=[('minimal', 'Minimal'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='low'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['template_type'],
                condition=models.Q(is_active=True),
                name='unique_active_template_per_type'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class UserSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    current_text = models.TextField(blank=True)
    translation_prompt = models.ForeignKey(
        PromptTemplate,
        related_name='translation_sessions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    analysis_prompt = models.ForeignKey(
        PromptTemplate,
        related_name='analysis_sessions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id}"


class AnalysisConfiguration(models.Model):
    word_group_threshold = models.IntegerField(
        default=4,
        help_text="Number of words or fewer that constitute a word group (vs sentence)"
    )
    sentence_threshold = models.IntegerField(
        default=20,
        help_text="Number of words or more that constitute a sentence for analysis purposes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Analysis Configuration"
        verbose_name_plural = "Analysis Configurations"

    def __str__(self):
        return f"Word Group: ≤{self.word_group_threshold} words, Sentence: ≥{self.sentence_threshold} words"

    @classmethod
    def get_current(cls):
        """Get the current analysis configuration, create default if none exists"""
        config = cls.objects.first()
        if not config:
            config = cls.objects.create()
        return config
