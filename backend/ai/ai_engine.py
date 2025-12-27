import vertexai
from vertexai.generative_models import GenerativeModel
import json

vertexai.init(project="devstreamai", location="us-central1")
model = GenerativeModel("gemini-2.5-flash")


def try_parse_json(raw: str):
    """Try to parse JSON, remove junk, fallback to model-based repair."""
    raw = raw.strip()

    # Remove code fences
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    # Remove leading 'json' token
    if raw.startswith("json\n"):
        raw = raw[5:].strip()

    # Try direct JSON parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # If parsing fails, ask model to FIX the JSON
    repair_prompt = f"""
You are a JSON repair engine. Fix the following JSON so that it becomes valid.

Return ONLY the corrected JSON, nothing else.

BROKEN JSON:
{raw}
"""

    repair_response = model.generate_content(repair_prompt)
    fixed = repair_response.text.strip()

    # Final attempt
    try:
        return json.loads(fixed)
    except:
        return {"error": "unfixable_json", "raw": raw, "repaired": fixed}


def analyze_failure(log_text: str, code_text: str):

    prompt = f"""
You MUST output ONLY valid JSON.
Follow this EXACT structure:

{{
  "explanation": "string",
  "root_cause": "string",
  "patch": "string"
}}

Rules:
- No backticks.
- No code fences.
- No markdown.
- No 'json' prefix.
- No trailing commas.
- Patch MUST begin with:
    --- original_file
    +++ fixed_file

Fix summarization:
CI/CD FAILURE LOG:
{log_text}

SOURCE CODE:
{code_text}
"""

    response = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": 2048, "temperature": 0.1}
    )

    return try_parse_json(response.text)
