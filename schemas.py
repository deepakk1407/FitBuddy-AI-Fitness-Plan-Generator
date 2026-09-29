from pydantic import BaseModel, Field, field_validator


class UserInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    user_id: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    age: int = Field(ge=13, le=100)
    weight: float = Field(gt=20, le=500)
    goal: str = Field(min_length=2, max_length=80)
    intensity: str = Field(min_length=3, max_length=20)

    @field_validator("goal", "intensity")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip().lower()


class FeedbackRequest(BaseModel):
    feedback: str = Field(min_length=5, max_length=2000)


class Exercise(BaseModel):
    name: str
    sets: int = Field(ge=1, le=10)
    reps_or_duration: str
    rest: str
    notes: str = ""


class DayPlan(BaseModel):
    day: str
    focus: str
    warmup: str
    exercises: list[Exercise]
    cooldown: str


class WorkoutPlan(BaseModel):
    overview: str
    safety_note: str
    days: list[DayPlan] = Field(min_length=7, max_length=7)


class NutritionTip(BaseModel):
    title: str
    tip: str
    hydration: str
    recovery: str
