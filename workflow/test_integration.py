"""测试集成 Storyboard Agent 后的 Workflow"""

import sys
from pathlib import Path

# Ensure workflow is in path
workflow_dir = Path(__file__).resolve().parent
if str(workflow_dir) not in sys.path:
    sys.path.insert(0, str(workflow_dir))

from main import run_ad_workflow

def test_workflow_integration():
    """
    测试 Storyboard Agent 集成后的完整工作流程
    
    Steps:
    1. Write ad script
    2. Run Storyboard Agent (black box)
    3. Generate videos sequentially
    4. Aggregate results
    5. Concatenate videos
    6. Generate BGM
    """
    print("\n" + "=" * 80)
    print("测试 Storyboard Agent 集成")
    print("=" * 80)
    
    # Test with minimal configuration
    result = run_ad_workflow(
        product_name="Running Shoes",
        brand_identity="Athletic, Energetic, Performance",
        product_images="https://cdn.discordapp.com/attachments/1073330837912821780/1439534000434708523/7e037bea93156e1017ae3fd60ad8eb8d.jpg",
        must_have_shots="Person running on track",
        generate_video=False,  # Start with False for faster testing
        video_model="kling"
    )
    
    print("\n" + "=" * 80)
    print("测试结果")
    print("=" * 80)
    
    # Verify key outputs
    assert "shots" in result, "Missing 'shots' in result"
    assert "episode_result" in result, "Missing 'episode_result' from Storyboard Agent"
    assert "nanobanana_images" in result, "Missing 'nanobanana_images' from Storyboard Agent"
    
    episode_result = result["episode_result"]
    print(f"\n✓ Storyboard Agent 输出:")
    print(f"  - Episode ID: {episode_result.episode_id}")
    print(f"  - Total Beats: {episode_result.total_beats}")
    print(f"  - Successful: {episode_result.successful_beats}")
    print(f"  - Flagged: {episode_result.flagged_beats}")
    
    nanobanana_images = result["nanobanana_images"]
    print(f"\n✓ 生成的合成图片:")
    print(f"  - 总数: {len(nanobanana_images)}")
    for i, url in enumerate(nanobanana_images, 1):
        print(f"  {i}. {url}")
    
    shot_results = result.get("shot_results", [])
    print(f"\n✓ 视频生成结果:")
    print(f"  - 总数: {len(shot_results)}")
    for shot_result in shot_results:
        print(f"  Beat {shot_result['beat_number']}: video_prompt={'有' if shot_result.get('video_prompt') else '无'}")
    
    print("\n" + "=" * 80)
    print("✅ 测试通过 - Storyboard Agent 成功集成!")
    print("=" * 80)
    
    return result

if __name__ == "__main__":
    test_workflow_integration()

