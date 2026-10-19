"""Generate synthetic receipt images plus a ground-truth CSV.

The images are drawn from scratch, so there are no licensing concerns, and
every field the model is asked to read has a known correct answer.

    python make_sample_images.py
"""

import csv
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent / "images"

RECEIPTS = [
    ("Blue Bottle Coffee", "2026-09-14", [("Latte", 5.50), ("Croissant", 4.25), ("Drip coffee", 3.75)], "png"),
    ("Corner Hardware", "2026-09-21", [("Wood screws 100ct", 8.99), ("Hammer", 19.49), ("Sandpaper pack", 6.25)], "jpg"),
    ("Green Leaf Market", "2026-10-02", [("Apples 2lb", 4.98), ("Oat milk", 3.49), ("Sourdough", 6.00), ("Eggs dozen", 5.29)], "png"),
    ("Metro Books", "2026-10-05", [("Paperback novel", 17.99), ("Bookmark", 2.50)], "jpg"),
    ("Sunset Diner", "2026-10-08", [("Cheeseburger", 13.50), ("Fries", 4.50), ("Milkshake", 6.75), ("Tip", 5.00)], "png"),
    ("City Pharmacy", "2026-10-11", [("Vitamin D", 11.99), ("Bandages", 4.79), ("Hand cream", 7.49)], "webp"),
]
TAX_RATE = 0.08


def draw_receipt(merchant: str, date: str, items: list[tuple[str, float]]) -> tuple[Image.Image, float]:
    font = ImageFont.load_default(size=22)
    title = ImageFont.load_default(size=30)
    width, line_h = 520, 34
    height = 260 + line_h * len(items) + 140
    img = Image.new("RGB", (width, height), (252, 250, 244))
    d = ImageDraw.Draw(img)

    y = 30
    d.text((width // 2, y), merchant.upper(), font=title, fill="black", anchor="mt")
    y += 50
    d.text((width // 2, y), f"Date: {date}", font=font, fill="black", anchor="mt")
    y += 50
    d.line((30, y, width - 30, y), fill="gray", width=2)
    y += 20

    subtotal = 0.0
    for name, price in items:
        d.text((40, y), name, font=font, fill="black")
        d.text((width - 40, y), f"${price:.2f}", font=font, fill="black", anchor="ra")
        subtotal += price
        y += line_h

    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)
    y += 10
    d.line((30, y, width - 30, y), fill="gray", width=2)
    y += 20
    for label, amount in [("Subtotal", subtotal), ("Tax 8%", tax), ("TOTAL", total)]:
        d.text((40, y), label, font=title if label == "TOTAL" else font, fill="black")
        d.text((width - 40, y), f"${amount:.2f}", font=title if label == "TOTAL" else font, fill="black", anchor="ra")
        y += line_h + (6 if label == "TOTAL" else 0)

    # Slight rotation so the task is closer to a real photo of a receipt.
    img = img.rotate(random.uniform(-2.5, 2.5), expand=True, fillcolor=(210, 210, 210))
    return img, total


def main() -> None:
    random.seed(7)
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    for i, (merchant, date, items, fmt) in enumerate(RECEIPTS, start=1):
        img, total = draw_receipt(merchant, date, items)
        file_name = f"receipt_{i:02d}.{fmt}"
        img.save(OUT_DIR / file_name, quality=90)
        rows.append({"file_name": file_name, "merchant": merchant, "date": date, "total": f"{total:.2f}"})

    with open(OUT_DIR.parent / "ground_truth.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} receipts to {OUT_DIR}")


if __name__ == "__main__":
    main()
