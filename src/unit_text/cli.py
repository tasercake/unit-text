import typer

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
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")
