from __future__ import annotations

from typing import Any
try:
    from google import genai
    from google.genai import types
except ImportError:  # Allows local unit tests to run before optional AI dependency is installed.
    genai = None
    types = None
from .config import settings
from .schemas import NutritionTip, UserInput, WorkoutPlan


class GeminiServiceError(RuntimeError):
    pass


class GeminiService:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.gemini_api_key) if (settings.gemini_api_key and genai is not None) else None

    def _require_client(self):
        if genai is None:
            raise GeminiServiceError("The google-genai package is not installed. Run: pip install -r requirements.txt")
        if self.client is None:
            raise GeminiServiceError("GEMINI_API_KEY is not configured. Add it to the .env file and restart the server.")
        return self.client

    @staticmethod
    def _generate(client, model: str, prompt: str, schema: type[Any]) -> Any:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=8000,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            if not response.text:
                raise GeminiServiceError("Gemini returned an empty response.")
            return schema.model_validate_json(response.text)
        except GeminiServiceError:
            raise
        except Exception as exc:
            raise GeminiServiceError(f"Gemini request failed: {exc}") from exc

    def generate_workout(self, user: UserInput) -> WorkoutPlan:
        client = self._require_client()
        prompt = f"""
You are FitBuddy, a cautious fitness-planning assistant. Create a practical 7-day workout plan.
User: name={user.name}, age={user.age}, weight={user.weight} kg, goal={user.goal}, intensity={user.intensity}.
Requirements:
- Exactly 7 days.
- Each day has warm-up, exercises, and cooldown.
- Exercises must include sets, reps or duration, rest, and a short note.
- Vary muscle groups and include appropriate rest/recovery.
- Respect the requested intensity without prescribing unsafe extremes.
- Do not diagnose, treat, or make medical claims.
- Include a brief safety note recommending professional advice for injuries or health conditions.
- Keep the plan readable and realistic for a general adult unless the user is under 18; for a minor, use conservative activity and recommend adult/professional guidance.
"""
        return self._generate(client, settings.gemini_workout_model, prompt, WorkoutPlan)

    def generate_nutrition_tip(self, user: UserInput) -> NutritionTip:
        client = self._require_client()
        prompt = f"""
Generate one concise wellness nutrition/recovery tip for a FitBuddy user.
Goal: {user.goal}; intensity: {user.intensity}; age: {user.age}; weight: {user.weight} kg.
Avoid calorie prescriptions, medical treatment, or extreme dieting. Emphasize balanced food, hydration and recovery.
Return a practical tip that complements a workout plan.
"""
        return self._generate(client, settings.gemini_fast_model, prompt, NutritionTip)

    def update_workout(self, user: UserInput, original_plan: str, feedback: str) -> WorkoutPlan:
        client = self._require_client()
        prompt = f"""
You are revising an existing FitBuddy 7-day workout plan.
User: name={user.name}, age={user.age}, weight={user.weight} kg, goal={user.goal}, intensity={user.intensity}.
Original plan:
{original_plan}

User feedback:
{feedback}

Create a revised 7-day plan. Preserve useful parts, apply the feedback, keep exactly 7 days,
and maintain safe, realistic general-wellness guidance. Do not diagnose or treat medical conditions.
"""
        return self._generate(client, settings.gemini_workout_model, prompt, WorkoutPlan)
