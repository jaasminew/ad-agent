import json

import pytest

from tools.nanobanana import NanobananaToolInput


def test_nanobanana_args_valid():
    payload = NanobananaToolInput.model_validate(
        {
            "prompt": "Replace the laptop...",
            "input_image_paths": [
                "https://example.com/storyboard.png",
                "https://example.com/product.png",
            ],
            "upload_to_cos": True,
        }
    )

    assert payload.prompt == "Replace the laptop..."
    assert payload.input_image_paths == [
        "https://example.com/storyboard.png",
        "https://example.com/product.png",
    ]
    assert payload.upload_to_cos is True


def test_nanobanana_args_double_encoded_prompt():
    nested = json.dumps(
        {
            "prompt": "Replace the laptop...",
            "input_image_paths": [
                "https://example.com/storyboard.png",
                "https://example.com/product.png",
            ],
            "upload_to_cos": False,
        }
    )

    payload = NanobananaToolInput.model_validate({"prompt": nested})

    assert payload.prompt == "Replace the laptop..."
    assert payload.input_image_paths == [
        "https://example.com/storyboard.png",
        "https://example.com/product.png",
    ]
    assert payload.upload_to_cos is False


def test_nanobanana_args_missing_input_image_paths():
    with pytest.raises(ValueError) as exc:
        NanobananaToolInput.model_validate({"prompt": "Replace the laptop..."})

    assert "requires `input_image_paths`" in str(exc.value)


def test_nanobanana_rejects_incomplete_discord_url():
    with pytest.raises(ValueError) as exc:
        NanobananaToolInput.model_validate(
            {
                "prompt": "Replace the laptop...",
                "input_image_paths": [
                    "https://cdn.discordapp.com/attachments/1439226094921322516/file.png",
                    "https://example.com/product.png",
                ],
            }
        )

    assert "Discord storyboard URL" in str(exc.value)


def test_nanobanana_accepts_full_discord_url():
    payload = NanobananaToolInput.model_validate(
        {
            "prompt": "Replace the laptop...",
            "input_image_paths": [
                "https://cdn.discordapp.com/attachments/1434024239719125184/1439226094921322516/file.png",
                "https://example.com/product.png",
            ],
        }
    )

    assert payload.input_image_paths[0].endswith("file.png")

