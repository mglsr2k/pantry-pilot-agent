# Pantry Pilot

Pantry Pilot is a domain-specific web chat agent that helps users decide what they can cook with ingredients they already have. The agent can search real recipes, compare a recipe against the user's pantry, and suggest practical adaptations.

## Tools

1. **`search_recipes`** — calls the Spoonacular recipe API using the user's ingredients. It returns recipe candidates with used/missing ingredients and a Spoonacular backlink.
2. **`get_recipe_details`** — calls Spoonacular for one selected recipe and retrieves its complete ingredient list, servings, preparation time, and source URL.
3. **`match_ingredients`** — a local Python tool that compares the selected recipe's ingredients with the user's pantry, calculates an approximate match percentage, identifies missing ingredients, and suggests possible substitutions.

The agent uses Gemini through Vertex AI to decide when to call tools and how to combine their results. Conversation history is stored by session so follow-up questions can use earlier context.

## Setup

### 1. Google Cloud / Gemini

Authenticate locally and select the Google Cloud project used for the assignment:

```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT_ID
```

### 2. Spoonacular API key — each team member creates their own key

Each person working on the project should create **their own Spoonacular API key**. Do not share or commit API keys to GitHub.

1. Create/sign in to your Spoonacular account.
2. Open the Spoonacular API dashboard.
3. Create/copy your API key.
4. In the project folder, create a local `.env` file from the example:

```bash
cp .env.example .env
```

5. Open `.env` and add your own key:

```text
SPOONACULAR_API_KEY=YOUR_PERSONAL_KEY
```

6. Save the file. The `.gitignore` file prevents `.env` from being committed to GitHub.

**Never put the actual API key in `tools.py`, `README.md`, GitHub, screenshots, or messages.** Each teammate can use a separate key on their own computer. The deployed Cloud Run application will receive its API key separately through its environment/secret configuration.

If you prefer not to create a `.env` file, you can also set the variable directly in your terminal:

```bash
export SPOONACULAR_API_KEY="YOUR_PERSONAL_KEY"
```

The free Spoonacular plan is limited, so avoid unnecessary repeated searches during testing.

### 3. Install/run locally

From the project folder:

```bash
uv run app.py
```

Then open `http://127.0.0.1:8000`.

## Example grader queries

1. `I have pasta, spinach, milk, garlic and Greek yogurt. I'm vegetarian and want something creamy. What can I make?`
2. `I have rice, chickpeas, tomatoes and onions. I'm vegan and want to use as many of these ingredients as possible.`
3. `I have potatoes, eggs and cheese. I don't have butter. What can I make, and what could I substitute for butter?`

## Important limitation

Dietary preferences and allergies are treated as user constraints by the agent, but the ingredient-search endpoint does not by itself prove that a recipe is allergy-safe. The agent should clearly state this limitation and should never guarantee that a suggested substitution is safe for an allergy.

## API attribution

Recipe results include a backlink to Spoonacular as required by the free API plan.
