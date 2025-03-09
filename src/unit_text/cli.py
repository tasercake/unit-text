import base64
import mimetypes
import re
from pathlib import Path
from typing import Annotated, Literal

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


def parse_file_to_message_blocks(
    file_path: Path,
    file_type: Literal["text", "markdown"] | None = None,
):
    """
    Parse a file and return its content as a list of messages in the OpenAI API format.

    Args:
        file_path: Path to the file
        file_type: Explicitly specify the file type (text or markdown)
                  If None, will be inferred from the file extension

    Returns:
        List of message blocks in OpenAI API format
    """
    # Infer file type if not provided
    if not file_type:
        suffix = file_path.suffix.lower()
        if suffix in [".md", ".markdown"]:
            file_type = "markdown"
        else:
            file_type = "text"

    # Read the content of the file
    content = file_path.read_text()

    if file_type == "text":
        return [{"role": "user", "content": content}]

    elif file_type == "markdown":
        # For markdown, we need to parse and handle images
        # First, let's create a list to hold our message content parts
        message_parts = []

        # Regular expression to find Markdown image syntax: ![alt](url)
        image_pattern = r"!\[(.*?)\]\((.*?)\)"

        # Split the content based on image tags
        last_end = 0
        for match in re.finditer(image_pattern, content):
            # Add text before the image
            if match.start() > last_end:
                text_before = content[last_end : match.start()]
                if text_before.strip():
                    message_parts.append({"type": "text", "text": text_before})

            # Extract image info
            alt_text = match.group(1)
            image_path = match.group(2)

            # Handle local image paths
            if not image_path.startswith(("http://", "https://")):
                # Resolve path relative to the markdown file
                img_full_path = file_path.parent / image_path
                if img_full_path.exists():
                    # Determine MIME type
                    mime_type, _ = mimetypes.guess_type(img_full_path)
                    if not mime_type:
                        mime_type = "image/jpeg"  # Default to JPEG if can't determine

                    # Read and encode image
                    with open(img_full_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode("utf-8")

                    # Add image to message parts
                    message_parts.append(
                        {
                            "type": "image",
                            "image_url": {"url": f"data:{mime_type};base64,{img_data}"},
                        }
                    )
                else:
                    # If image doesn't exist, include as text
                    img_reference = f"![{alt_text}]({image_path})"
                    message_parts.append({"type": "text", "text": img_reference})
            else:
                # For remote images, just include the URL
                message_parts.append(
                    {"type": "image", "image_url": {"url": image_path}}
                )

            last_end = match.end()

        # Add any remaining text after the last image
        if last_end < len(content):
            remaining_text = content[last_end:]
            if remaining_text.strip():
                message_parts.append({"type": "text", "text": remaining_text})

        return message_parts

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


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

    # Convert the idea to XML format for inclusion in the user message
    xml_idea = dicttoxml(idea.model_dump(), attr_type=False, custom_root="idea")

    # Get file content as content parts
    file_content_parts = parse_file_to_message_blocks(file)

    # Create content starting with idea XML as a text block
    content_parts = [{"type": "text", "text": xml_idea}]

    # Add all file content parts (text and images) in their original order
    content_parts.extend(file_content_parts)

    # Create the complete user message
    user_message = {"role": "user", "content": content_parts}

    # Create messages list with system and user messages
    messages = [{"role": "system", "content": system_message}, user_message]

    # Result will be stored here
    result_json = None

    # Create appropriate client based on provider
    if provider == ModelProvider.openai:
        client = openai.OpenAI(api_key=SETTINGS.openai_api_key)
        response = client.beta.chat.completions.parse(
            model=model_to_use,
            messages=messages,
            response_format=TestResult,
            temperature=0,
        )
        result_json = response.choices[0].message.content
    elif provider == ModelProvider.ollama:
        base_url = "http://localhost:11434/v1"
        client = openai.OpenAI(
            base_url=base_url,
            api_key="ollama",  # required but unused
        )
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            # response_format={"json_schema": TestResult.model_json_schema()},
            temperature=0,
        )
        result_json = response.choices[0].message.content

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
