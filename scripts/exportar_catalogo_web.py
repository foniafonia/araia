#!/usr/bin/env python3
"""Exporta un catalogo JSON apto para la web estatica de GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXCEL = ROOT / 'base_datos' / 'pictogramas.xlsx'
OUTPUT = ROOT / 'catalogo_web.json'


def main() -> None:
    dataframe = pd.read_excel(EXCEL, engine='openpyxl').fillna('')
    records = []
    for row in dataframe.to_dict(orient='records'):
        absolute_path = Path(str(row.get('ruta_archivo', ''))).resolve()
        try:
            relative_path = absolute_path.relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            continue
        if not absolute_path.exists() or not relative_path.startswith('pictogramas/'):
            continue
        records.append(
            {
                'id': int(row.get('id', 0)) if str(row.get('id', '')).strip() else 0,
                'palabra': str(row.get('palabra', '')).strip(),
                'variante': str(row.get('variante', '')).strip(),
                'categoria_gramatical': str(row.get('categoria_gramatical', '')).strip(),
                'subcategoria': str(row.get('subcategoria', '')).strip(),
                'categoria_semantica': str(row.get('categoria_semantica', '')).strip(),
                'descripcion': str(row.get('descripcion', '')).strip(),
                'fecha_creacion': str(row.get('fecha_creacion', '')).strip(),
                'image_path': relative_path,
            }
        )

    payload = {
        'generated_at': pd.Timestamp.now().isoformat(),
        'count': len(records),
        'records': records,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Exportado: {OUTPUT}')


if __name__ == '__main__':
    main()
