from pydantic import BaseModel


class IdeaModel(BaseModel):
    """Represents an idea for a piece of writing."""

    topic: str
    audience: str
    audience_knowledge: str
    audience_care: str
    desired_action: str
    goal: str
    perspective: str


class Evaluation(BaseModel):
    """The evaluation and suggestions for a specific aspect of a piece of writing."""

    evaluation: str
    suggestions: str


class TestResult(BaseModel):
    """The results of a test on a piece of writing."""

    clarity: Evaluation
    alignment_with_objectives: Evaluation
    completeness: Evaluation
    overall_suggestions: str
