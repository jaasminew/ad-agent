# Image Generation Agent — Architecture & Workflow

## Overview

The Image Generation Agent transforms script beats into product-integrated advertisement images. It generates storyboard frames, validates quality, and seamlessly replaces objects with product images.

---

## Tools & Components

### 1. **PixelHub** (`tools/pixelhub.py`)
- **Purpose:** Find reference images that match the scene description
- **Input:** Shot description, optional style hint
- **Output:** Reference image URL + color palette

### 2. **MidJourney** (`tools/midjourney.py`)
- **Purpose:** Generate storyboard images from prompts
- **Input:** Text prompt, style reference, negative prompts
- **Output:** Generated image URL

### 3. **Distortion Checker** (`tools/distortion_checker/`)
- **Purpose:** Quality control - detect anatomical distortions
- **Input:** Image URL
- **Output:** Pass/fail verdict with distortion labels and bounding boxes

### 4. **Nanobanana** (`tools/nanobanana.py`)
- **Purpose:** Replace objects in images with product images
- **Input:** Storyboard image + product image + replacement prompt
- **Output:** Final product-integrated image URL (uploaded to COS)

### 5. **Memory** (`tools/memory.py`)
- **Purpose:** Persist episode state and beat results
- **Storage:** Episode palette, beat metadata, final URLs

### 6. **COS Uploader** (`tools/cos_uploader.py`)
- **Purpose:** Upload final images to cloud storage
- **Note:** Already integrated in nanobanana, may be used for additional uploads

---

## Agent Workflow

### Input
```json
{
  "title": "Episode Title",
  "product_config": {
    "product_image_url": "https://...",
    "target_object": "laptop"
  },
  "beats": [
    {
      "beat": 1,
      "heading": "Scene Title",
      "shot description": "Scene description",
      "action": "What happens"
    }
  ]
}
```

### Processing Steps (Per Beat)

#### **Step 1: Normalize Beat**
- Extract: `heading`, `shot description`, `action`
- Combine into `shot_text`: `"{heading} — {shot description}. Action: {action}"`

#### **Step 2: Get Reference Image**
- **Tool:** `pixelhub.py`
- **Action:** Search for reference image matching `shot_text`
- **Extract:** 
  - `reference_image_url`
  - `color_palette` (hex codes)

#### **Step 3: Manage Episode Palette**
- **First beat:** Store `color_palette` from reference as `episode_palette`
- **Subsequent beats:** Reuse stored `episode_palette`
- **Tool:** `memory.py` to persist palette

#### **Step 4-6: ReAct Loop (Max 3 Attempts)**

**Loop starts:**

##### **Step 4: Generate Storyboard Image**
- **Tool:** `midjourney.py`
- **Input:**
  - Prompt: `shot_text + "cinematic composition, natural light, realistic proportions"`
  - Style reference: `reference_image_url`
  - Palette anchors: Derived from `episode_palette`
  - Negative prompts: `["extra fingers", "malformed hands", "warped limbs", "deformed face"]`
- **Output:** `storyboard_image_url`

##### **Step 5: Quality Check**
- **Tool:** `distortion_checker/`
- **Input:** `storyboard_image_url`
- **Output:** 
  - `pass: true/false`
  - `distortion_labels: []` (if any issues)
  - `bboxes: []` (where issues are)

##### **Step 6: Agent Decision**
- **If PASS:** Exit loop → Go to Step 7
- **If FAIL:**
  - Add detected distortion labels to negative prompts
  - If bboxes provided: Use MidJourney inpaint
  - Else: Regenerate full image
  - If attempt 2 fails: Switch to alternate reference
  - If attempt 3 fails: Store best attempt, flag for review, continue to next beat

**Loop ends**

#### **Step 7: Product Replacement**
- **Tool:** `nanobanana.py`
- **Input:**
  - Image 1: `storyboard_image_url` (approved frame)
  - Image 2: `product_config.product_image_url`
  - Prompt: `"Replace the {target_object} in the scene with the product image. Maintain lighting, shadows, and perspective. Preserve artistic style."`
- **Output:** `final_image_url` (uploaded to COS)
- **Error Handling:**
  - Retry once with simplified prompt
  - If both fail: Use `storyboard_image_url`, flag `product_replacement_failed`

#### **Step 8: Save Results**
- **Tool:** `memory.py`
- **Store:**
  - `beat_number`
  - `storyboard_image_url` (before product)
  - `final_image_url` (after product)
  - `product_replacement_success: true/false`
  - Generation attempts count
  - All generation parameters

### Output
```json
{
  "episode_id": "xxx",
  "beats": [
    {
      "beat_number": 1,
      "storyboard_image_url": "https://midjourney.../image.png",
      "final_image_url": "https://cos.../nanobanana_xxx.png",
      "product_replacement_success": true
    }
  ]
}
```

---

## Visual Flow

```
Input: Script Beat + Product Config
    ↓
[1] Normalize → shot_text
    ↓
[2] PixelHub → reference_image + palette
    ↓
[3] Memory → store/load episode_palette
    ↓
[4-6] ReAct Loop (max 3×):
    ├─ [4] MidJourney → generate storyboard_image
    ├─ [5] Distortion Checker → validate
    └─ [6] Decision: PASS→exit | FAIL→retry
    ↓
[7] Nanobanana → replace object with product
    (storyboard_image + product_image → final_image)
    ↓
[8] Memory → save all results
    ↓
Output: final_image_url (product-integrated)
```

---

## Key Design Decisions

### 1. Episode Palette Consistency
- First beat establishes color palette
- All subsequent beats reuse same palette
- Ensures visual consistency across entire episode

### 2. ReAct Pattern for Quality
- Agent reasons about distortion feedback
- Decides: accept, regenerate, or inpaint
- Maximum 3 attempts prevents infinite loops

### 3. Product Replacement as Final Step
- Only happens after storyboard passes quality check
- No additional distortion check (trust Nanobanana)
- Fallback to original storyboard if replacement fails

### 4. Dual Image Storage
- `storyboard_image_url`: Original frame (pre-product)
- `final_image_url`: Product-integrated (post-nanobanana)
- Allows review of both stages

---

## Implementation Files Structure

```
/ad-agent/
├── image_gen_agent.py          # Main agent class (ReAct logic)
├── prompt_engineer.py          # Prompt composition utilities
├── episode_manager.py          # Episode palette & state management
└── tools/                      # Already prepared
    ├── pixelhub.py            ✓ Reference search
    ├── midjourney.py          ✓ Image generation
    ├── distortion_checker/    ✓ Quality control
    ├── nanobanana.py          ✓ Product replacement
    ├── memory.py              ✓ State persistence
    └── cos_uploader.py        ✓ Cloud upload
```

