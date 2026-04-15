from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1200
HEIGHT = 680
BG_COLOR = (11, 18, 32)
TEXT_COLOR = (235, 242, 250)
MUTED_TEXT = (170, 184, 205)
BOX_FILL = (28, 38, 61)
BOX_OUTLINE = (90, 123, 181)
ACTIVE_FILL = (44, 63, 98)
ACTIVE_OUTLINE = (117, 185, 255)
ARROW_COLOR = (145, 168, 205)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "arial.ttf",
        "segoeui.ttf",
        "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    left, top, right, bottom = box
    text_box = draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=6)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    x = left + (right - left - text_w) // 2
    y = top + (bottom - top - text_h) // 2
    draw.multiline_text((x, y), text, font=font, fill=fill, align="center", spacing=6)


def _draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line([start, end], fill=ARROW_COLOR, width=5)
    ex, ey = end
    arrow_size = 14
    draw.polygon(
        [
            (ex, ey),
            (ex - arrow_size, ey - arrow_size // 2),
            (ex - arrow_size, ey + arrow_size // 2),
        ],
        fill=ARROW_COLOR,
    )


def _box(
    draw: ImageDraw.ImageDraw,
    coords: tuple[int, int, int, int],
    label: str,
    active: bool,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    fill = ACTIVE_FILL if active else BOX_FILL
    outline = ACTIVE_OUTLINE if active else BOX_OUTLINE
    draw.rounded_rectangle(coords, radius=26, fill=fill, outline=outline, width=4)
    _draw_centered_text(draw, coords, label, body_font, TEXT_COLOR)


def render_frame(active_step: int, title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont, body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    draw.text((40, 28), "Agentic Review Gate: End-to-End Flow", fill=TEXT_COLOR, font=title_font)
    draw.text(
        (40, 88),
        "Parallel agents write findings to shared state, then summarizer posts a GitHub review comment.",
        fill=MUTED_TEXT,
        font=body_font,
    )

    webhook = (90, 210, 350, 350)
    logic = (420, 150, 700, 290)
    security = (420, 370, 700, 510)
    blackboard = (770, 250, 1060, 410)
    summary = (420, 540, 700, 650)
    comment = (770, 500, 1060, 650)

    _box(draw, webhook, "GitHub PR Event\n/webhook/github", active_step == 0, body_font)
    _box(draw, logic, "Logic Agent\n(patterns, complexity)", active_step == 1, body_font)
    _box(draw, security, "Security Agent\n(secrets, OWASP)", active_step == 2, body_font)
    _box(draw, blackboard, "ReviewState\n(shared findings)", active_step == 3, body_font)
    _box(draw, summary, "Summarizer Agent\n(dedupe + rank)", active_step == 4, body_font)
    _box(draw, comment, "Final GitHub\nPR Comment", active_step == 5, body_font)

    _draw_arrow(draw, (350, 280), (420, 220))
    _draw_arrow(draw, (350, 280), (420, 440))
    _draw_arrow(draw, (700, 220), (770, 300))
    _draw_arrow(draw, (700, 440), (770, 360))
    _draw_arrow(draw, (915, 410), (700, 595))
    _draw_arrow(draw, (700, 595), (770, 575))

    steps = [
        "1) Receive GitHub pull request event",
        "2) Run Logic Agent analysis",
        "3) Run Security Agent analysis",
        "4) Merge findings on blackboard state",
        "5) Summarizer synthesizes final message",
        "6) Post review-ready GitHub comment",
    ]
    draw.text((40, 620), steps[active_step], fill=(142, 226, 176), font=body_font)
    return image


def main() -> None:
    title_font = _font(42)
    body_font = _font(26)

    frames: list[Image.Image] = []
    for step in range(6):
        frame = render_frame(step, title_font, body_font)
        frames.extend([frame] * 5)

    output = Path(__file__).resolve().parents[1] / "docs" / "assets" / "agentic-review-workflow.gif"
    output.parent.mkdir(parents=True, exist_ok=True)

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=180,
        loop=0,
        optimize=True,
    )
    print(f"Created: {output}")


if __name__ == "__main__":
    main()
