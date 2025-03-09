from pathlib import Path
from typing import Annotated

import ollama
import openai
import typer
from dicttoxml import dicttoxml
from rich import print
from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .models import Evaluation, IdeaModel, ModelProvider, TestResult
from .settings import SETTINGS

app = typer.Typer(
    short_help="Unit tests for prose",
    help="""
    [bold green]unit-text[/] helps you write unit tests for prose.
    It uses :sparkles: agents :sparkles: to ensure
    that you meet the target audience's expectations,
    and that your writing achieves the desired outcomes.
    """,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

OptConfig = Annotated[Path, typer.Option(help="The config file for the idea.")]
default_config = Path("unit-text.json")


@app.command()
def ideate(config: OptConfig = default_config):
    """Generate ideas for your writing."""
    print("I'll ask you a few questions to prepare for your writing.")

    existing_idea = (
        IdeaModel.model_validate_json(config.read_text())
        if config.exists()
        else IdeaModel(
            topic=None,
            audience=None,
            audience_knowledge=None,
            audience_care=None,
            desired_action=None,
            goal=None,
            perspective=None,
        )
    )

    topic = Prompt.ask(
        "What is the [bold green]topic[/]?",
        default=existing_idea.topic,
    )
    audience = Prompt.ask(
        "Who is your intended [bold red]audience[/]?",
        default=existing_idea.audience,
    )
    audience_knowledge = Prompt.ask(
        "What does your audience already know about the [bold green]topic[/]?",
        default=existing_idea.audience_knowledge,
    )
    audience_care = Prompt.ask(
        "Why do they care about what you're writing?",
        default=existing_idea.audience,
    )
    desired_action = Prompt.ask(
        "What do you want them to do differently after reading your writing?",
        default=existing_idea.desired_action,
    )

    goal = Prompt.ask(
        "What's the goal of this blog post?",
        default=existing_idea.goal,
    )
    perspective = Prompt.ask(
        "Why is your perspective on this [bold green]topic[/] interesting?",
        default=existing_idea.perspective,
    )

    idea = IdeaModel(
        topic=topic,
        audience=audience,
        audience_knowledge=audience_knowledge,
        audience_care=audience_care,
        desired_action=desired_action,
        goal=goal,
        perspective=perspective,
    )

    config.write_text(idea.model_dump_json(indent=2))

    print(f"[bold yellow]Idea[/] written to {config}")


@app.command()
def test(
    file: Path,
    config: OptConfig = default_config,
    provider: Annotated[
        ModelProvider,
        typer.Option(help="Model provider to use: ollama, openai"),
    ] = ModelProvider.ollama,
    model: Annotated[
        str,
        typer.Option(
            help="Specific model to use (defaults to provider's default model)"
        ),
    ] = None,
):
    """Test the input file."""
    print("Running tests...")

    # Default models for each provider
    default_models = {
        ModelProvider.ollama: "deepseek-r1:7b",
        ModelProvider.openai: "gpt-4o",
    }

    # Use the provided model or fall back to the default for the selected provider
    model_to_use = model or default_models[provider]

    print(f"Using {provider} with model {model_to_use}")

    idea = IdeaModel.model_validate_json(config.read_text())

    xml_idea = dicttoxml(idea.model_dump(), attr_type=False, custom_root="idea")

    body = {"draft": file.read_text()}
    xml_body = dicttoxml(body, attr_type=False, root=False)

    prompt = f"""
    {xml_idea}
    
    {xml_body}
    """

    system_message = """
You are an experienced technical writer and editor
with expertise in developer-focused content.
Your role is to provide detailed, actionable feedback on blog posts,
focusing on both technical accuracy and engaging writing style.

When reviewing a blog post, analyze it against the following criteria:

1. Clarity:
   - Is the main message clear and well-articulated?
   - Are technical concepts explained appropriately for the target audience?
   - Is the writing style engaging and accessible?
   - Are there any confusing or ambiguous sections?

2. Alignment with Objectives:
   - Does the content match the stated goals and target audience?
   - Is the technical depth appropriate for the intended readers?
   - Are the examples and analogies relevant and helpful?
   - Does the post deliver on its promises?

3. Completeness:
   - Are all key points fully developed?
   - Is there a clear introduction and conclusion?
   - Are code examples (if any) complete and well-explained?
   - Are there any missing or unnecessary sections?

4. Overall Suggestions:
   - Specific improvements for structure and flow
   - Recommendations for enhancing engagement
   - Suggestions for technical accuracy or depth
   - Ideas for better examples or analogies

For each evaluation, return a `test_passed` boolean
to indicate if the content was good enough for that specific aspect.

Keep your feedback constructive but honest.
Focus on specific, actionable improvements rather than general observations.
Reference specific parts of the text when making suggestions.
"""

    # Call the appropriate API based on the provider
    if provider == ModelProvider.ollama:
        response = ollama.chat(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            format=TestResult.model_json_schema(),
            options=ollama.Options(
                temperature=0,  # to ensure consistent results
                num_ctx=8192,  # to ensure the entire text is processed
            ),
        )
        result_json = response.message.content

    elif provider == ModelProvider.openai:
        client = openai.OpenAI(api_key=SETTINGS.openai_api_key)
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            response_format=TestResult,
            temperature=0,
        )
        result_json = response.choices[0].message.content

    else:
        raise ValueError(f"Unsupported provider: {provider}")

    out = TestResult.model_validate_json(result_json)

    def evaluation_panel(evaluation: Evaluation, title: str) -> Panel:
        return Panel(
            Group(
                Panel(
                    Markdown(evaluation.evaluation),
                    title="Evaluation",
                    style="blue",
                ),
                Panel(
                    Markdown(evaluation.suggestions),
                    title="Suggestions",
                    style="green",
                ),
            ),
            title=f"""{title} ({
                "[bold green]Passed[/]"
                if evaluation.test_passed
                else "[bold red]Failed[/]"
            })""",
        )

    panel_group = Group(
        evaluation_panel(
            out.clarity,
            title="Clarity",
        ),
        evaluation_panel(
            out.alignment_with_objectives,
            title="Alignment with Objectives",
        ),
        evaluation_panel(
            out.completeness,
            title="Completeness",
        ),
        Panel(
            Markdown(out.overall_suggestions),
            title="Overall Suggestions",
        ),
    )
    print(panel_group)
