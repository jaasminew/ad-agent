"""BGM Generator Worker - Generate and add background music to final video"""

import logging
import re
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .state import WorkflowState
from langchain_openai import ChatOpenAI
from tools.suno_music import suno_generate_music
from tools.video_add_bgm import add_bgm_to_video

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"BGM Generator (LLM): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_music_prompt_with_retry(llm, product_name: str, brand_identity: str, shots_text: str) -> str:
    """Generate music prompt with retry mechanism."""
    music_prompt_generation = f"""你是一位专业的广告音乐顾问。请根据以下广告内容,生成一个适合作为背景音乐的 Suno 提示词。

商品名称: {product_name}
品牌定位: {brand_identity}

广告分镜:
{shots_text}

要求:
1. 分析商品定位和品牌调性
2. 结合所有分镜的情绪和节奏
3. 生成符合广告氛围的音乐描述
4. 确定音乐风格(如:轻快、舒缓、激昂、科技感、优雅、活力等)
5. 这将是纯音乐(无歌词),适合作为广告背景音乐

请直接输出音乐提示词,不要包含任何解释或额外文字。提示词应该简洁、具体,能够让 AI 音乐生成模型理解。

示例格式: "一段轻快明亮的电子音乐,富有科技感和未来感,节奏感强烈但不嘈杂,适合科技产品广告"
"""
    
    response = llm.invoke(music_prompt_generation)
    return response.content.strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"BGM Generator (Style): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _detect_music_style_with_retry(llm, music_prompt: str) -> str:
    """Detect music style with retry mechanism."""
    style_detection_prompt = f"""根据以下音乐描述,从以下选项中选择最合适的音乐风格标签:

可选风格: 古典, 流行, 摇滚, 电子, 爵士, 轻音乐, 氛围音乐, 电影配乐, 新世纪, 放克, 雷鬼, 乡村, 布鲁斯

音乐描述: {music_prompt}

请只输出一个最合适的风格标签,不要包含任何其他文字。"""
    
    response = llm.invoke(style_detection_prompt)
    return response.content.strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    retry=retry_if_exception_type((Exception, RuntimeError)),
    before_sleep=lambda retry_state: logger.warning(
        f"BGM Generator (Suno API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_music_with_suno_retry(music_prompt: str, music_style: str, music_title: str) -> str:
    """Generate music with Suno API with retry mechanism."""
    music_result = suno_generate_music.invoke({
        "prompt": music_prompt,
        "style": music_style,
        "title": music_title,
        "instrumental": True,  # Pure music, no lyrics
        "model": "V3_5",
        "upload_to_cos": True,
    })
    
    # Parse the result to extract BGM URL
    if isinstance(music_result, str):
        if music_result.startswith("Error:"):
            raise RuntimeError(music_result)
        
        # Try to extract URL from the result string
        url_match = re.search(r'URL:\s*(https?://\S+)', music_result)
        if url_match:
            return url_match.group(1)
        else:
            # If URL pattern not found, try to find Local Path
            path_match = re.search(r'Local Path:\s*(.+\.mp3)', music_result)
            if path_match:
                return path_match.group(1).strip()
            else:
                raise RuntimeError("Could not extract BGM URL from Suno result")
    else:
        raise RuntimeError(f"Unexpected Suno result format: {type(music_result)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=3, max=15),
    retry=retry_if_exception_type((Exception, RuntimeError)),
    before_sleep=lambda retry_state: logger.warning(
        f"BGM Generator (Add BGM): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _add_bgm_to_video_with_retry(final_video_url: str, bgm_url: str, output_filename: str) -> str:
    """Add BGM to video with retry mechanism."""
    return add_bgm_to_video(
        video_url=final_video_url,
        audio_url=bgm_url,
        output_filename=output_filename,
        audio_volume=0.3,  # 30% volume
        fade_out_duration=2.0  # Fade out last 2 seconds
    )


def generate_and_add_bgm(state: WorkflowState) -> dict:
    """
    Generate background music and add it to the final video.
    
    This worker runs after video concatenation. It only performs BGM generation
    if generate_video is True and final_video_url exists.
    
    Steps:
    1. Use LLM to generate music prompt based on ad content
    2. Call Suno API to generate background music
    3. Add BGM to the final video using ffmpeg
    4. Upload the final video with BGM to COS
    
    Inputs:
    - final_video_url: URL of the concatenated video (from step 8)
    - video_duration: Video duration in seconds
    - generate_video: Whether to generate video
    - product_name: Product name
    - brand_identity: Brand identity
    - shots: List of shot descriptions
    
    Outputs:
    - music_prompt: Generated music prompt
    - bgm_url: URL of generated background music
    - final_video_with_bgm_url: URL of final video with BGM
    """
    logger.info("=== BGM Generator: Checking if BGM generation is needed ===")
    
    generate_video_flag = state.get("generate_video", False)
    final_video_url = state.get("final_video_url")
    
    if not generate_video_flag:
        logger.info("Video generation is disabled (generate_video=False), skipping BGM generation")
        return {
            "messages": ["✓ BGM Generator: Skipped (video generation disabled)"]
        }
    
    if not final_video_url:
        logger.warning("No final video URL found, cannot add BGM")
        return {
            "messages": ["⚠ BGM Generator: No final video to add BGM to"]
        }
    
    # BGM generation is needed, proceed
    logger.info("BGM generation is enabled, proceeding...")
    
    product_name = state.get("product_name", "product")
    brand_identity = state.get("brand_identity", "")
    shots = state.get("shots", [])
    
    # Step 1: Generate music prompt using LLM
    logger.info("Step 1: Generating music prompt using LLM...")
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        
        # Prepare context for LLM
        shots_text = "\n".join([f"{i+1}. {shot}" for i, shot in enumerate(shots)])
        
        music_prompt = _generate_music_prompt_with_retry(llm, product_name, brand_identity, shots_text)
        
        logger.info("=" * 80)
        logger.info("✓ Music prompt generated successfully!")
        logger.info(f"Music Prompt: {music_prompt}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Failed to generate music prompt: {e}", exc_info=True)
        return {
            "messages": [f"✗ BGM Generator: Failed to generate music prompt - {str(e)}"]
        }
    
    # Step 2: Determine music style from prompt
    logger.info("Step 2: Determining music style...")
    
    try:
        music_style = _detect_music_style_with_retry(llm, music_prompt)
        logger.info(f"Detected music style: {music_style}")
        
    except Exception as e:
        logger.warning(f"Failed to detect music style, using default: {e}")
        music_style = "电子"  # Default style
    
    # Step 3: Generate music using Suno
    logger.info("Step 3: Generating background music with Suno...")
    
    try:
        # Generate a title for the music
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        music_title = f"{product_name}_BGM_{timestamp}"
        
        # Call Suno to generate music
        logger.info(f"Calling Suno API...")
        logger.info(f"  Prompt: {music_prompt}")
        logger.info(f"  Style: {music_style}")
        logger.info(f"  Title: {music_title}")
        
        bgm_url = _generate_music_with_suno_retry(music_prompt, music_style, music_title)
        
        logger.info("=" * 80)
        logger.info("✓ Background music generated successfully!")
        logger.info(f"BGM URL: {bgm_url}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Failed to generate background music: {e}", exc_info=True)
        return {
            "music_prompt": music_prompt,
            "messages": [f"✗ BGM Generator: Failed to generate music - {str(e)}"]
        }
    
    # Step 4: Add BGM to video
    logger.info("Step 4: Adding background music to video...")
    
    try:
        # Sanitize product name for filename
        safe_product_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_product_name = safe_product_name.replace(' ', '_')
        output_filename = f"{safe_product_name}_final_with_bgm_{timestamp}"
        
        logger.info(f"Adding BGM to video...")
        logger.info(f"  Video: {final_video_url}")
        logger.info(f"  BGM: {bgm_url}")
        logger.info(f"  Output: {output_filename}")
        
        # Use the convenience function with retry
        final_video_with_bgm_url = _add_bgm_to_video_with_retry(final_video_url, bgm_url, output_filename)
        
        logger.info("=" * 80)
        logger.info("✓ Background music added to video successfully!")
        logger.info(f"Final video with BGM: {final_video_with_bgm_url}")
        logger.info("=" * 80)
        
        return {
            "music_prompt": music_prompt,
            "music_style": music_style,
            "bgm_url": bgm_url,
            "final_video_with_bgm_url": final_video_with_bgm_url,
            "messages": [
                f"✓ BGM Generator: Generated music with style '{music_style}'",
                f"✓ BGM Generator: Added BGM to final video"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to add BGM to video: {e}", exc_info=True)
        return {
            "music_prompt": music_prompt,
            "music_style": music_style,
            "bgm_url": bgm_url,
            "messages": [f"✗ BGM Generator: Failed to add BGM to video - {str(e)}"]
        }

