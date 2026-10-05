"""Tools exposed to the cooking agent and the Python functions that run them."""

import json
import os
import re
import urllib.parse

import requests

SPOONACULAR_URL = "https://api.spoonacular.com/recipes/findByIngredients"

# Simple, conservative substitution suggestions. These are suggestions for
# cooking adaptation, NOT allergy-safe guarantees.
SUBSTITUTIONS = {
    "heavy cream": ["whole milk + a little butter", "evaporated milk", "plain Greek yogurt"],
    "heavy whipping cream": ["whole milk + a little butter", "evaporated milk", "plain Greek yogurt"],
    "cream": ["evaporated milk", "whole milk + a little butter", "plain Greek yogurt"],
    "butter": ["olive oil", "neutral cooking oil"],
    "milk": ["unsweetened soy milk", "unsweetened oat milk", "unsweetened almond milk"],
    "sour cream": ["plain Greek yogurt"],
    "mayonnaise": ["plain Greek yogurt", "avocado"],
    "parmesan cheese": ["pecorino romano", "nutritional yeast"],
    "lemon juice": ["lime juice", "white wine vinegar"],
    "lime juice": ["lemon juice", "white wine vinegar"],
}


def _clean(text: str) -> str:
    """Normalize ingredient text for simple matching."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def search_recipes(
    ingredients: list[str],
    dietary_preferences: list[str] | None = None,
    allergies: list[str] | None = None,
    ranking: str = "minimize_missing_ingredients",
) -> str:
    """Search Spoonacular using the ingredients the user has.

    This uses one Spoonacular request and returns the ingredients that the API
    says are already used and missing. Dietary preferences and allergies are
    returned to the agent as constraints; the agent must not claim that the
    Spoonacular ingredient endpoint has verified allergy safety.
    """
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "Spoonacular API key is missing. Set SPOONACULAR_API_KEY in your environment."
        })

    ingredients = [i.strip() for i in ingredients if i and i.strip()]
    if not ingredients:
        return json.dumps({"error": "Please provide at least one ingredient."})

    ranking = ranking if ranking in {"maximize_used_ingredients", "minimize_missing_ingredients"} else "minimize_missing_ingredients"
    params = {
        "apiKey": api_key,
        "ingredients": ",".join(ingredients[:12]),
        "number": 5,
        "ranking": 1 if ranking == "maximize_used_ingredients" else 2,
        "ignorePantry": "true",
    }

    try:
        response = requests.get(SPOONACULAR_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return json.dumps({"error": f"Recipe search failed: {exc}"})
    except ValueError:
        return json.dumps({"error": "Recipe service returned invalid JSON."})

    recipes = []
    for item in data if isinstance(data, list) else []:
        recipes.append({
            "name": item.get("title"),
            "recipe_id": item.get("id"),
            "image": item.get("image"),
            "used_ingredients": [x.get("original", x.get("name", "")) for x in item.get("usedIngredients", [])],
            "missing_ingredients": [x.get("original", x.get("name", "")) for x in item.get("missedIngredients", [])],
            "used_ingredient_count": item.get("usedIngredientCount", 0),
            "missing_ingredient_count": item.get("missedIngredientCount", 0),
            "source_url": (
                "https://spoonacular.com/recipes/"
                + urllib.parse.quote(re.sub(r"[^a-z0-9]+", "-", (item.get("title") or "recipe").lower()).strip("-"))
                + "-" + str(item.get("id"))
            ),
        })

    return json.dumps({
        "query_ingredients": ingredients,
        "requested_dietary_preferences": dietary_preferences or [],
        "requested_allergies": allergies or [],
        "ranking": ranking,
        "result_count": len(recipes),
        "recipes": recipes,
        "note": (
            "Spoonacular's find-by-ingredients endpoint identifies used and missing ingredients. "
            "Dietary preferences and allergies are user constraints, not guarantees of safety. "
            "Do not claim a recipe is allergy-safe or that a substitution is allergy-safe without verification. "
            "Recipe results should include a Spoonacular backlink in the final response when a recipe link is available."
        ),
    })


def match_ingredients(user_ingredients: list[str], recipe_ingredients: list[str]) -> str:
    """Compare ingredients the user has with a recipe and suggest adaptations."""
    user = [_clean(x) for x in user_ingredients if x and x.strip()]
    recipe = [x.strip() for x in recipe_ingredients if x and x.strip()]

    if not recipe:
        return json.dumps({"error": "The recipe has no ingredient list to compare."})

    available = []
    missing = []
    substitution_candidates = []

    for original in recipe:
        normalized = _clean(original)
        found = any(u in normalized or normalized in u for u in user if u)
        if found:
            available.append(original)
            continue

        missing.append(original)
        for ingredient, substitutes in SUBSTITUTIONS.items():
            if ingredient in normalized:
                substitution_candidates.append({
                    "missing_ingredient": original,
                    "possible_substitutions": substitutes,
                    "caveat": "Check quantities and dietary/allergy constraints before substituting.",
                })
                break

    match_percent = round(100 * len(available) / len(recipe))

    return json.dumps({
        "match_percent": match_percent,
        "available_ingredients": available,
        "missing_ingredients": missing,
        "possible_substitutions": substitution_candidates,
        "note": "Ingredient matching is approximate because recipe text and user ingredient names vary.",
    })


# What Gemini sees: the tool names, descriptions, and argument schemas.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_recipes",
            "description": (
                "Search Spoonacular for real recipes using ingredients the user has. "
                "Use this when recipe candidates are needed. It makes one external API request "
                "and returns recipes with used and missing ingredients. The tool passes dietary preferences and "
                "allergies are constraints to consider, but this endpoint does not by itself prove "
                "a recipe is allergy-safe. Do not invent recipe search results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ingredients the user currently has or wants to use.",
                    },
                    "dietary_preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferences such as vegetarian, vegan, or gluten-free.",
                    },
                    "allergies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Allergies or ingredients the user must avoid, such as peanuts or dairy.",
                    },
                    "ranking": {
                        "type": "string",
                        "enum": ["maximize_used_ingredients", "minimize_missing_ingredients"],
                        "description": "Choose maximize_used_ingredients when the user wants to use up what they have; choose minimize_missing_ingredients when they want the fewest extra purchases.",
                    },
                },
                "required": ["ingredients"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "match_ingredients",
            "description": (
                "Compare the user's ingredients with a candidate recipe's ingredient list. Use this "
                "after finding a recipe to identify what the user already has, what is missing, an "
                "approximate match percentage, and possible cooking substitutions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ingredients available to the user.",
                    },
                    "recipe_ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ingredient lines from a candidate recipe.",
                    },
                },
                "required": ["user_ingredients", "recipe_ingredients"],
            },
        },
    },
]


TOOL_MAP = {
    "search_recipes": search_recipes,
    "match_ingredients": match_ingredients,
}


def run_tool(name: str, args: dict) -> str:
    """Run a model-requested tool without letting tool errors crash the agent loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except TypeError as exc:
        return json.dumps({"error": f"Bad arguments for {name}: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"Tool {name} failed: {type(exc).__name__}: {str(exc)[:300]}"})
