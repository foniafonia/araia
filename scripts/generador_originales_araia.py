#!/usr/bin/env python3
"""Generador base de pictogramas originales Araia.

Este script no pretende producir lotes masivos automaticamente.
Su funcion es ofrecer una base consistente para construir familias de pictos
con mejor calidad que los iconos improvisados.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS = 768
BLACK = "#111111"
WHITE = "white"


class AraiaCanvas:
    """Lienzo simple con utilidades de estilo compartido."""

    def __init__(self) -> None:
        self.image = Image.new("RGBA", (CANVAS, CANVAS), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        try:
            self.font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 82)
        except Exception:
            self.font = None

    def label(self, text: str) -> None:
        bbox = self.draw.textbbox((0, 0), text, font=self.font)
        width = bbox[2] - bbox[0]
        self.draw.text(((CANVAS - width) / 2, 625), text, fill=BLACK, font=self.font)

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(target)
        return target

    def line(self, points, width: int = 12) -> None:
        self.draw.line(points, fill=BLACK, width=width, joint="curve")

    def outlined_round_rect(self, box, fill: str, radius: int = 18, width: int = 12) -> None:
        self.draw.rounded_rectangle(box, radius=radius, fill=fill, outline=BLACK, width=width)

    def outlined_ellipse(self, box, fill: str, width: int = 12) -> None:
        self.draw.ellipse(box, fill=fill, outline=BLACK, width=width)


def draw_book() -> AraiaCanvas:
    """Ejemplo de pictograma con una estructura mas controlada."""
    canvas = AraiaCanvas()
    d = canvas.draw
    d.rounded_rectangle((185, 250, 380, 520), radius=18, fill="#4D96FF", outline=BLACK, width=12)
    d.rounded_rectangle((388, 250, 583, 520), radius=18, fill="#6BCB77", outline=BLACK, width=12)
    d.line((384, 250, 384, 520), fill=BLACK, width=12)
    for y in (320, 370, 420):
        d.line((240, y, 330, y), fill=BLACK, width=8)
        d.line((438, y, 528, y), fill=BLACK, width=8)
    canvas.label("LIBRO")
    return canvas


def draw_notebook() -> AraiaCanvas:
    canvas = AraiaCanvas()
    d = canvas.draw
    canvas.outlined_round_rect((205, 190, 555, 530), fill="#F7B267", radius=22)
    canvas.line((280, 190, 280, 530), width=10)
    for y in range(235, 505, 50):
        canvas.outlined_ellipse((230, y, 260, y + 30), fill=WHITE, width=8)
    for y in (270, 330, 390, 450):
        canvas.line((320, y, 490, y), width=8)
    canvas.label("CUADERNO")
    return canvas


def draw_pencil() -> AraiaCanvas:
    canvas = AraiaCanvas()
    d = canvas.draw
    d.polygon([(195, 470), (390, 190), (520, 320), (325, 600)], fill="#F4C95D", outline=BLACK)
    d.polygon([(195, 470), (235, 615), (325, 600)], fill="#E2B36C", outline=BLACK)
    d.polygon([(205, 510), (225, 580), (265, 570)], fill="#D9D9D9", outline=BLACK)
    d.polygon([(225, 580), (235, 615), (265, 570)], fill="#4A4A4A", outline=BLACK)
    d.polygon([(390, 190), (470, 110), (600, 240), (520, 320)], fill="#EF476F", outline=BLACK)
    canvas.line((350, 250, 520, 420), width=10)
    canvas.label("LAPIZ")
    return canvas


def draw_clock() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_ellipse((184, 150, 584, 550), fill="#F7FBFF")
    for angle_box in [
        (372, 175, 396, 235),
        (372, 465, 396, 525),
        (210, 338, 270, 362),
        (498, 338, 558, 362),
    ]:
        canvas.outlined_round_rect(angle_box, fill=BLACK, radius=8, width=2)
    canvas.line((384, 350, 384, 235), width=14)
    canvas.line((384, 350, 468, 395), width=14)
    canvas.outlined_ellipse((360, 326, 408, 374), fill=BLACK, width=6)
    canvas.label("RELOJ")
    return canvas


def draw_scissors() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_ellipse((210, 390, 320, 500), fill="#9AD1FF")
    canvas.outlined_ellipse((330, 390, 440, 500), fill="#9AD1FF")
    canvas.line((300, 420, 520, 250), width=14)
    canvas.line((350, 420, 560, 540), width=14)
    canvas.outlined_ellipse((490, 220, 550, 280), fill="#D9D9D9", width=10)
    canvas.outlined_ellipse((530, 510, 590, 570), fill="#D9D9D9", width=10)
    canvas.label("TIJERAS")
    return canvas


def draw_phone() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_round_rect((255, 140, 513, 565), fill="#2F3C4F", radius=32)
    canvas.outlined_round_rect((285, 185, 483, 485), fill="#AEE2FF", radius=18, width=10)
    canvas.outlined_ellipse((360, 502, 408, 550), fill="#D9D9D9", width=8)
    canvas.line((342, 166, 426, 166), width=8)
    canvas.label("TELEFONO")
    return canvas


def draw_key() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_ellipse((190, 255, 350, 415), fill="#FFD166")
    canvas.outlined_ellipse((230, 295, 310, 375), fill=WHITE, width=10)
    canvas.outlined_round_rect((318, 318, 560, 352), fill="#FFD166", radius=12)
    canvas.outlined_round_rect((500, 352, 540, 400), fill="#FFD166", radius=8)
    canvas.outlined_round_rect((438, 352, 478, 390), fill="#FFD166", radius=8)
    canvas.label("LLAVE")
    return canvas


def draw_bottle() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_round_rect((300, 165, 468, 560), fill="#8ED6FF", radius=28)
    canvas.outlined_round_rect((338, 115, 430, 195), fill="#8ED6FF", radius=18)
    canvas.outlined_round_rect((338, 100, 430, 130), fill="#5C7AEA", radius=10, width=10)
    canvas.line((320, 300, 448, 300), width=8)
    canvas.line((320, 375, 448, 375), width=8)
    canvas.label("BOTELLA")
    return canvas


def draw_brush() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_round_rect((250, 180, 520, 300), fill="#4D96FF", radius=26)
    for x in range(270, 501, 24):
        canvas.line((x, 300, x, 430), width=10)
    canvas.outlined_round_rect((285, 430, 485, 490), fill="#FFD166", radius=14)
    canvas.label("CEPILLO")
    return canvas


def draw_cup() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_round_rect((240, 240, 500, 470), fill="#FFB703", radius=22)
    canvas.outlined_ellipse((470, 280, 590, 400), fill=WHITE, width=12)
    canvas.outlined_ellipse((500, 310, 560, 370), fill=WHITE, width=10)
    canvas.line((260, 240, 480, 240), width=10)
    canvas.label("TAZA")
    return canvas


def draw_balloon() -> AraiaCanvas:
    canvas = AraiaCanvas()
    canvas.outlined_ellipse((235, 145, 535, 445), fill="#EF476F")
    canvas.draw.polygon([(360, 425), (408, 425), (384, 470)], fill="#EF476F", outline=BLACK)
    canvas.line((384, 470, 384, 575), width=8)
    canvas.label("GLOBO")
    return canvas


if __name__ == "__main__":
    export_dir = Path(__file__).resolve().parent.parent / "exportaciones"
    outputs = [
        draw_book().save(export_dir / "libro_plantilla_araia.png"),
        draw_notebook().save(export_dir / "cuaderno_plantilla_araia.png"),
        draw_pencil().save(export_dir / "lapiz_plantilla_araia.png"),
        draw_clock().save(export_dir / "reloj_plantilla_araia.png"),
        draw_scissors().save(export_dir / "tijeras_plantilla_araia.png"),
        draw_phone().save(export_dir / "telefono_plantilla_araia.png"),
        draw_key().save(export_dir / "llave_plantilla_araia.png"),
        draw_bottle().save(export_dir / "botella_plantilla_araia.png"),
        draw_brush().save(export_dir / "cepillo_plantilla_araia.png"),
        draw_cup().save(export_dir / "taza_plantilla_araia.png"),
        draw_balloon().save(export_dir / "globo_plantilla_araia.png"),
    ]
    for output in outputs:
        print(output)
