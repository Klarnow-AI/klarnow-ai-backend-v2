from app.modules.packs.logo_generation import (
    LOGO_PROMPT_MAX_LENGTH,
    _extract_generated_image_payload,
    _truncate_logo_prompt,
)


def test_extract_generated_image_payload_accepts_direct_image_url_string() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Generated the logo.",
                    "images": [
                        {
                            "type": "image_url",
                            "image_url": "data:image/png;base64,QUJDRA==",
                        }
                    ],
                }
            }
        ]
    }

    assert _extract_generated_image_payload(response) == (
        "data_url",
        "data:image/png;base64,QUJDRA==",
        None,
    )


def test_extract_generated_image_payload_accepts_inline_data_parts() -> None:
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": "QUJDRA==",
                            }
                        }
                    ]
                }
            }
        ]
    }

    assert _extract_generated_image_payload(response) == (
        "base64",
        "QUJDRA==",
        "image/png",
    )


def test_truncate_logo_prompt_preserves_head_and_tail() -> None:
    prompt = "HEAD " + ("middle " * 300) + "TAIL"

    truncated = _truncate_logo_prompt(prompt)

    assert len(truncated) <= LOGO_PROMPT_MAX_LENGTH
    assert truncated.startswith("HEAD ")
    assert truncated.endswith("TAIL")
    assert " ... " in truncated
