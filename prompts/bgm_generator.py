"""Prompts for BGM Generator Worker"""

def get_music_prompt_generation(product_name: str, brand_identity: str, shots_text: str) -> str:
    """Generate music prompt for BGM generation"""
    return f"""You are a professional advertising music consultant. Based on the following advertisement content, generate a suitable Suno prompt for background music.

Product Name: {product_name}
Brand Identity: {brand_identity}

Advertisement Shots:
{shots_text}

Requirements:
1. Analyze the product positioning and brand tone
2. Combine the emotions and rhythm of all shots
3. Generate a music description that fits the advertisement atmosphere
4. Determine the music style (e.g., upbeat, soothing, energetic, tech-feel, elegant, vibrant, etc.)
5. This will be instrumental music (no lyrics), suitable as advertisement background music

Please output the music prompt directly without any explanations or extra text. The prompt should be concise, specific, and understandable for AI music generation models.

Example format: "An upbeat and bright electronic music piece with a strong sense of technology and futurism, rhythmic but not noisy, suitable for tech product advertisements"
"""


def get_style_detection_prompt(music_prompt: str) -> str:
    """Generate style detection prompt"""
    return f"""Based on the following music description, select the most appropriate music style tag from the options below:

Available Styles: Classical, Pop, Rock, Electronic, Jazz, Easy Listening, Ambient, Film Score, New Age, Funk, Reggae, Country, Blues

Music Description: {music_prompt}

Please output only one most appropriate style tag without any other text."""

