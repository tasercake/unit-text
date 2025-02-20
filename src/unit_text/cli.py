from pathlib import Path
from typing import Annotated

import ollama
import typer
from dicttoxml import dicttoxml
from rich import print
from rich.console import Group
from rich.panel import Panel
from rich.prompt import Prompt

from .models import Evaluation, IdeaModel, TestResult

app = typer.Typer(
    short_help="Unit tests for prose",
    help="""
    [bold green]unit-text[/bold green] helps you write unit tests for prose.
    It uses :sparkles: agents :sparkles: to ensure
    that you meet the target audience's expectations,
    and that your writing achieves the desired outcomes.
    """,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.command()
def ideate(
    output: Annotated[
        Path, typer.Option(help="The output file to write the ideas to.")
    ] = Path("unit-text.json"),
):
    """Generate ideas for your writing."""
    print("I'll ask you a few questions to prepare for your writing.")

    topic = Prompt.ask("What is the [bold green]topic[/]?")
    audience = Prompt.ask("Who is your intended [bold red]audience[/]?")
    audience_knowledge = Prompt.ask(
        "What does your audience already know about the [bold green]topic[/]?"
    )
    audience_care = Prompt.ask("Why do they care about what you're writing?")
    desired_action = Prompt.ask(
        "What do you want them to do differently after reading your writing?"
    )

    goal = Prompt.ask("What's the goal of this blog post?")
    perspective = Prompt.ask(
        "Why is your perspective on this [bold green]topic[/] interesting?"
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

    output.write_text(idea.model_dump_json())

    print(f"Idea written to {output}")


@app.command()
def test(
    file: Path,
    config: Annotated[Path, typer.Option(help="The config file.")] = Path(
        "unit-text.json"
    ),
):
    """Test the input file."""
    print("Running tests...")

    idea = IdeaModel.model_validate_json(config.read_text())

    xml_idea = dicttoxml(idea.model_dump(), attr_type=False, custom_root="idea")

    body = {"draft": file.read_text()}
    xml_body = dicttoxml(body, attr_type=False, root=False)

    prompt = f"""
    Given a blog post idea and a draft,
    analyze whether the draft meets the stated objectives.
    
    {xml_idea}
    
    {xml_body}
    
    Provide structured feedback in this format:
    1. Clarity: [Evaluation + Suggested improvements]
    2. Alignment with objectives: [Evaluation + Suggested changes]
    3. Completeness: [Evaluation + What’s missing or redundant]
    4. Overall Suggestions: [General feedback]
    """

    response = ollama.chat(
        model="deepseek-r1:7b",
        messages=[
            {"role": "system", "content": "You are a helpful technical writer"},
            {"role": "user", "content": prompt},
        ],
        format=TestResult.model_json_schema(),
        options={"temperature": 0},
    )

    out = TestResult.model_validate_json(response.message.content)

    def evaluation_panel(evaluation: Evaluation, title: str) -> Panel:
        return Panel(
            Group(
                Panel(evaluation.evaluation, title="Evaluation", style="blue"),
                Panel(evaluation.suggestions, title="Suggestions", style="green"),
            ),
            title=title,
        )

    panel_group = Group(
        evaluation_panel(out.clarity, title="Clarity"),
        evaluation_panel(
            out.alignment_with_objectives, title="Alignment with Objectives"
        ),
        evaluation_panel(out.completeness, title="Completeness"),
        Panel(out.overall_suggestions, title="Overall Suggestions"),
    )
    print(panel_group)
