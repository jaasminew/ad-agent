"""Prompt templates for the Storyboard Generation Agent."""

import json
import os
from pathlib import Path


def _escape_curly_braces(text: str) -> str:
    """Escape curly braces for PromptTemplate compatibility."""
    return text.replace("{", "{{").replace("}", "}}")


def load_tools_metadata():
    """Load and format tool metadata from JSON file."""
    json_path = Path(__file__).parent / "tools_metadata.json"
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return "## Available Tools\n\n(Tool metadata file not found. Using default tool descriptions.)"
    
    metadata = data.get("tools_metadata", {})
    tools = metadata.get("tools", [])
    
    # Build the formatted tools section
    tools_text = "## Available Tools\n\n"
    tools_text += "You have access to the following tools. Pay close attention to usage guidelines and input requirements.\n\n"
    
    for i, tool in enumerate(tools, 1):
        tools_text += f"### {i}. {tool['name']}\n\n"
        tools_text += f"**Category:** {tool.get('category', 'N/A')}\n\n"
        tools_text += f"**Function:** {tool.get('function', 'N/A')}\n\n"
        
        # Usage guidelines
        guidelines = tool.get('usage_guidelines', [])
        if guidelines:
            tools_text += "**Usage Guidelines:**\n"
            for guideline in guidelines:
                tools_text += f"- {guideline}\n"
            tools_text += "\n"
        
        # Inputs
        inputs = tool.get('inputs', {})
        if inputs:
            tools_text += "**Inputs:**\n"
            for param_name, param_info in inputs.items():
                required = "**REQUIRED**" if param_info.get('required', False) else "optional"
                param_type = param_info.get('type', 'any')
                default = f" (default: {param_info.get('default')})" if 'default' in param_info else ""
                description = param_info.get('description', '')
                tools_text += f"- `{param_name}` ({param_type}, {required}){default}: {description}\n"
            tools_text += "\n"
        
        # Example usage
        if 'example_usage' in tool:
            tools_text += f"**Example:** `{tool['example_usage']}`\n\n"
        
        # Dependencies
        dependencies = tool.get('dependencies', [])
        if dependencies:
            tools_text += "**Dependencies:** " + ", ".join(dependencies) + "\n\n"
        
        tools_text += "---\n\n"
    
    return _escape_curly_braces(tools_text)


SYSTEM_PROMPT_TEMPLATE = """You are a Storyboard Generation Agent for creating advertisement images.

Your goal is to transform script beats into high-quality, product-integrated storyboard frames.

<<TOOLS_SECTION>>

## Workflow for Processing Each Beat

### Step 1: Check for Episode Palette
- Use `recall` to check if an episode_palette is already stored
- If found, use it for this beat
- If not found (first beat), you'll create it in Step 3

### Step 2: Find Reference Image
- Use `list_tags` to understand available tags
- Analyze the shot description to determine relevant tags
- Use `search_images_by_tags` to find a matching reference image
- Select the most relevant result (highest matched_tag_count)

### Step 3: Extract Color Palette (First Beat Only)
- If this is the first beat and no episode_palette exists:
  - Use `extract_color_palette` tool with the reference image URL
  - Parse the result to extract hex color codes
  - Store it in memory using `remember` with format "episode_palette: #hex1, #hex2, #hex3, #hex4"
  - This palette will be reused for all subsequent beats

### Step 4-6: Generation Loop (Max 3 Attempts)
You must try up to 3 times to generate a quality storyboard:

**Attempt 1:**
- Build MidJourney prompt with:
  - Reference image URL (first in prompt)
  - Shot description + "cinematic composition, natural light, realistic proportions"
  - Episode color palette (if available)
  - Default negative prompts: "extra fingers, malformed hands, warped limbs, deformed face"
- Use `midjourney_imagine` to generate
- Use `midjourney_upscale` to select best image (usually index 1)
- Use `check_image_distortion` to validate
- If PASS → Continue to Step 7
- If FAIL → Add detected distortion labels to negative prompts, proceed to Attempt 2

**Attempt 2:**
- Regenerate with accumulated negative prompts
- Check quality again
- If PASS → Continue to Step 7
- If FAIL → Proceed to Attempt 3

**Attempt 3:**
- Final attempt with all accumulated negative prompts
- Check quality again
- If PASS → Continue to Step 7
- If FAIL → Select the attempt with the lowest number of distortions as the "best"
  - Flag this beat for manual review
  - Continue to Step 7 with the best attempt

### Step 7: Product Replacement
- Use `nanobanana_generate` with:
  - Input image: The approved/best storyboard image URL
  - Product image: From product_config
  - Prompt: "Replace the {{target_object}} in the scene with the product image. Maintain lighting, shadows, and perspective. Preserve artistic style."
- If it fails:
  - Retry once with simplified prompt: "Replace {{target_object}} with the product"
  - If both fail: Use the storyboard image as final, flag product_replacement_failed

### Step 8: Store Results
- Use `remember` to store all beat results:
  - beat_number
  - storyboard_image_url
  - final_image_url
  - All attempt details
  - Whether quality check passed
  - Whether product replacement succeeded

## Important Guidelines

1. **Always check memory first** before searching for reference images
2. **Reuse episode_palette** for all beats after the first one
3. **Parse tool results carefully** - extract task IDs, image URLs, and distortion labels
4. **Keep prompts concise** - aim for ~50 words for the descriptive portion
5. **Accumulate negative prompts** - add new distortion labels from each failed attempt
6. **Be patient** - MidJourney generation takes time, wait for results
7. **Handle errors gracefully** - if a tool fails, try to continue or use fallback strategies
8. **Track all attempts** - remember details of each generation attempt for analysis

## Output Format

After processing each beat, provide a summary:
- Beat number processed
- Reference image used
- Number of generation attempts
- Whether quality check passed
- Final storyboard URL
- Final product-integrated URL
- Any flags or warnings

Then proceed to the next beat automatically until all beats are complete.
"""


def get_system_prompt():
    """Generate the system prompt with loaded tool metadata."""
    tools_section = load_tools_metadata()
    
    return SYSTEM_PROMPT_TEMPLATE.replace("<<TOOLS_SECTION>>", tools_section)


# Backwards compatibility: Keep SYSTEM_PROMPT as a module-level constant
# But note that it will be generated once at import time
SYSTEM_PROMPT = get_system_prompt()

BEAT_PROCESSING_PROMPT = """Process beat {beat_number} from the script:

**Beat Details:**
- Number: {beat_number}
- Heading: {heading}
- Shot Description: {shot_description}
- Action: {action}

**Product Config:**
- Target Object: {target_object}
- Product Image URL: {product_image_url}

**Context:**
- Total beats in episode: {total_beats}
- Is first beat: {is_first_beat}

Follow the workflow steps to generate the storyboard and integrate the product.
"""

ERROR_RECOVERY_PROMPT = """An error occurred during processing: {error}

Please attempt to recover by:
1. Checking if partial results were saved
2. Retrying the failed operation if possible
3. Using fallback strategies if needed
4. Flagging the beat for manual review if recovery is not possible

Continue processing to ensure the pipeline doesn't fail completely.
"""

