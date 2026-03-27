#!/usr/bin/env python3
"""Gestor de biblioteca de pictogramas.

Este modulo crea y mantiene una biblioteca organizada de pictogramas
con un catalogo Excel centralizado.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import time
import unicodedata
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


ROOT_PATH = Path(__file__).resolve().parent.parent
PICTOGRAMAS_PATH = ROOT_PATH / "pictogramas"
BASE_DATOS_PATH = ROOT_PATH / "base_datos"
SCRIPTS_PATH = ROOT_PATH / "scripts"
EXPORTACIONES_PATH = ROOT_PATH / "exportaciones"
ENTRADAS_CONTINUAS_PATH = ROOT_PATH / "entradas_continuas"
ENTRADAS_PROCESADAS_PATH = ENTRADAS_CONTINUAS_PATH / "procesadas"
ENTRADAS_RECHAZADAS_PATH = ENTRADAS_CONTINUAS_PATH / "rechazadas"
EXCEL_PATH = BASE_DATOS_PATH / "pictogramas.xlsx"
LOCK_PATH = BASE_DATOS_PATH / "pictogramas.lock"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
DEFAULT_VARIANT = "blanco_y_negro"
VARIANT_ALIASES = {
    "": DEFAULT_VARIANT,
    "bn": "blanco_y_negro",
    "blanco_y_negro": "blanco_y_negro",
    "blanco y negro": "blanco_y_negro",
    "blancoynegro": "blanco_y_negro",
    "color": "color",
}

COLUMNAS = [
    "id",
    "palabra",
    "variante",
    "categoria_gramatical",
    "subcategoria",
    "genero",
    "numero",
    "categoria_semantica",
    "edad_recomendada",
    "dificultad",
    "descripcion",
    "ruta_archivo",
    "fecha_creacion",
]

ESTRUCTURA: Dict[str, List[str]] = {
    "sustantivos": ["animales", "personas", "objetos", "alimentos", "lugares", "naturaleza"],
    "verbos": ["acciones_diarias", "movimiento", "comunicacion", "emociones"],
    "adjetivos": ["tamano", "color", "emociones", "cualidades"],
    "pronombres": [],
    "preposiciones": [],
    "fonologia": ["fonemas", "articulacion", "praxias"],
    "conceptos": [],
}

DISPLAY_SUBCATEGORIES = {
    "tamano": "tamaño",
}

ALIAS_CATEGORIAS = {
    "sustantivo": "sustantivos",
    "sustantivos": "sustantivos",
    "verbo": "verbos",
    "verbos": "verbos",
    "adjetivo": "adjetivos",
    "adjetivos": "adjetivos",
    "pronombre": "pronombres",
    "pronombres": "pronombres",
    "preposicion": "preposiciones",
    "preposiciones": "preposiciones",
    "fonologia": "fonologia",
    "fonologico": "fonologia",
    "concepto": "conceptos",
    "conceptos": "conceptos",
}


def normalize_text(value: str) -> str:
    """Normaliza texto para comparaciones y nombres consistentes."""
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def slugify(value: str) -> str:
    """Genera nombres de archivo seguros y estables."""
    slug = normalize_text(value)
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "pictograma"


def display_subcategory(value: str) -> str:
    """Devuelve el nombre de carpeta real para una subcategoria."""
    key = normalize_text(value)
    return DISPLAY_SUBCATEGORIES.get(key, key)


def normalize_variant(value: str) -> str:
    """Normaliza la variante visual del pictograma."""
    normalized = normalize_text(value).replace("_", " ")
    return VARIANT_ALIASES.get(normalized, DEFAULT_VARIANT)


def create_directory_tree() -> None:
    """Crea toda la estructura del proyecto si falta alguna carpeta."""
    for directory in [
        ROOT_PATH,
        PICTOGRAMAS_PATH,
        BASE_DATOS_PATH,
        SCRIPTS_PATH,
        EXPORTACIONES_PATH,
        ENTRADAS_CONTINUAS_PATH,
        ENTRADAS_PROCESADAS_PATH,
        ENTRADAS_RECHAZADAS_PATH,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    for categoria, subcategorias in ESTRUCTURA.items():
        category_path = PICTOGRAMAS_PATH / categoria
        category_path.mkdir(parents=True, exist_ok=True)
        for subcategoria in subcategorias:
            (category_path / display_subcategory(subcategoria)).mkdir(parents=True, exist_ok=True)


def initialize_excel() -> None:
    """Inicializa el Excel con el esquema esperado."""
    if not EXCEL_PATH.exists():
        pd.DataFrame(columns=COLUMNAS).to_excel(EXCEL_PATH, index=False, engine="openpyxl")


def load_database() -> pd.DataFrame:
    """Carga el Excel y asegura la compatibilidad del esquema."""
    initialize_excel()
    try:
        dataframe = pd.read_excel(EXCEL_PATH, engine="openpyxl").fillna("")
    except (ValueError, zipfile.BadZipFile):
        backup_name = EXCEL_PATH.with_name(
            f"{EXCEL_PATH.stem}.corrupto.{datetime.now().strftime('%Y%m%d_%H%M%S')}{EXCEL_PATH.suffix}"
        )
        shutil.move(str(EXCEL_PATH), str(backup_name))
        pd.DataFrame(columns=COLUMNAS).to_excel(EXCEL_PATH, index=False, engine="openpyxl")
        dataframe = pd.read_excel(EXCEL_PATH, engine="openpyxl").fillna("")
    for column in COLUMNAS:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe[COLUMNAS]


def save_database(dataframe: pd.DataFrame) -> None:
    """Guarda el Excel usando un reemplazo atomico simple."""
    temp_path = EXCEL_PATH.with_suffix(".tmp.xlsx")
    dataframe.to_excel(temp_path, index=False, engine="openpyxl")
    temp_path.replace(EXCEL_PATH)


@contextmanager
def excel_lock(timeout_seconds: int = 20, poll_interval: float = 0.2):
    """Evita escrituras concurrentes sobre el catalogo Excel."""
    start = time.time()
    lock_fd = None

    while True:
        try:
            lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"No se pudo adquirir el bloqueo del Excel en {LOCK_PATH}")
            time.sleep(poll_interval)

    try:
        yield
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()


def next_id(dataframe: pd.DataFrame) -> int:
    """Calcula el siguiente identificador incremental."""
    if dataframe.empty:
        return 1
    numeric_ids = pd.to_numeric(dataframe["id"], errors="coerce").dropna()
    if numeric_ids.empty:
        return 1
    return int(numeric_ids.max()) + 1


def resolve_category(categoria_gramatical: str, subcategoria: str) -> Tuple[str, str]:
    """Valida categoria y subcategoria para ubicar el pictograma."""
    category_key = normalize_text(categoria_gramatical)
    category = ALIAS_CATEGORIAS.get(category_key)
    if not category:
        raise ValueError(f"Categoria no valida: {categoria_gramatical}")

    normalized_subcategory = normalize_text(subcategoria)
    valid_subcategories = ESTRUCTURA[category]

    if not valid_subcategories:
        return category, ""

    if normalized_subcategory not in valid_subcategories:
        raise ValueError(
            f"Subcategoria no valida para {category}: {subcategoria}. "
            f"Usa una de: {', '.join(valid_subcategories)}"
        )

    return category, display_subcategory(normalized_subcategory)


def infer_metadata_from_path(file_path: Path) -> Tuple[str, str]:
    """Infere categoria y subcategoria a partir de la ruta del archivo."""
    try:
        relative = file_path.relative_to(PICTOGRAMAS_PATH)
    except ValueError:
        return "", ""

    parts = relative.parts
    category = parts[0] if len(parts) >= 2 else ""
    subcategory = ""
    if category in ESTRUCTURA and ESTRUCTURA[category] and len(parts) >= 3:
        subcategory = parts[1]
    return category, subcategory


def split_word_and_variant(file_name_stem: str) -> Tuple[str, str]:
    """Separa la palabra base y la variante desde el nombre de archivo."""
    normalized_stem = normalize_text(file_name_stem)
    if normalized_stem.endswith("_color"):
        return file_name_stem[: -len("_color")], "color"
    if normalized_stem.endswith("_bn"):
        return file_name_stem[: -len("_bn")], DEFAULT_VARIANT
    return file_name_stem, DEFAULT_VARIANT


def upsert_record(dataframe: pd.DataFrame, record: Dict[str, str]) -> pd.DataFrame:
    """Inserta o actualiza el registro a partir de la ruta del archivo."""
    existing_index = dataframe.index[dataframe["ruta_archivo"] == record["ruta_archivo"]].tolist()
    if existing_index:
        row = existing_index[0]
        for column in COLUMNAS:
            if record.get(column, "") != "":
                dataframe.at[row, column] = record[column]
        return dataframe

    return pd.concat([dataframe, pd.DataFrame([record], columns=COLUMNAS)], ignore_index=True)


def crear_pictograma(
    palabra: str,
    categoria_gramatical: str,
    subcategoria: str,
    genero: str,
    numero: str,
    categoria_semantica: str,
    descripcion: str,
    edad_recomendada: str = "",
    dificultad: str = "",
    variante: str = DEFAULT_VARIANT,
) -> str:
    """Registra un pictograma nuevo y devuelve la ruta destino del PNG."""
    create_directory_tree()
    category, resolved_subcategory = resolve_category(categoria_gramatical, subcategoria)
    resolved_variant = normalize_variant(variante)
    variant_suffix = "" if resolved_variant == DEFAULT_VARIANT else "_color"
    filename = f"{slugify(palabra)}{variant_suffix}.png"
    if resolved_subcategory:
        file_path = PICTOGRAMAS_PATH / category / resolved_subcategory / filename
    else:
        file_path = PICTOGRAMAS_PATH / category / filename

    with excel_lock():
        dataframe = load_database()
        record = {
            "id": next_id(dataframe),
            "palabra": palabra,
            "variante": resolved_variant,
            "categoria_gramatical": category,
            "subcategoria": resolved_subcategory,
            "genero": genero,
            "numero": numero,
            "categoria_semantica": categoria_semantica,
            "edad_recomendada": edad_recomendada,
            "dificultad": dificultad,
            "descripcion": descripcion,
            "ruta_archivo": str(file_path),
            "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
        }

        save_database(upsert_record(dataframe, record))
    return str(file_path)


def crear_pictograma_desde_archivo(
    origen_archivo: str,
    palabra: str,
    categoria_gramatical: str,
    subcategoria: str,
    genero: str,
    numero: str,
    categoria_semantica: str,
    descripcion: str,
    edad_recomendada: str = "",
    dificultad: str = "",
    variante: str = DEFAULT_VARIANT,
) -> str:
    """Copia un archivo al catalogo y lo registra en el destino correcto."""
    source_path = Path(origen_archivo).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"No existe el archivo fuente: {source_path}")
    if source_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Formato de imagen no soportado: {source_path.suffix}")

    target_path = Path(
        crear_pictograma(
            palabra=palabra,
            categoria_gramatical=categoria_gramatical,
            subcategoria=subcategoria,
            genero=genero,
            numero=numero,
            categoria_semantica=categoria_semantica,
            descripcion=descripcion,
            edad_recomendada=edad_recomendada,
            dificultad=dificultad,
            variante=variante,
        )
    )
    shutil.copy2(source_path, target_path)
    return str(target_path)


def iter_image_files(base_path: Path) -> Iterable[Path]:
    """Recorre todas las imagenes de la biblioteca de forma escalable."""
    for root, _, files in os.walk(base_path):
        for filename in files:
            extension = Path(filename).suffix.lower()
            if extension in IMAGE_EXTENSIONS:
                yield Path(root) / filename


def scan_library() -> pd.DataFrame:
    """Escanea la biblioteca y sincroniza las imagenes con el Excel."""
    create_directory_tree()
    with excel_lock():
        dataframe = load_database()

        for file_path in iter_image_files(PICTOGRAMAS_PATH):
            category, subcategory = infer_metadata_from_path(file_path)
            base_word, variant = split_word_and_variant(file_path.stem)
            record = {
                "id": next_id(dataframe),
                "palabra": base_word,
                "variante": variant,
                "categoria_gramatical": category,
                "subcategoria": subcategory,
                "genero": "",
                "numero": "",
                "categoria_semantica": "",
                "edad_recomendada": "",
                "dificultad": "",
                "descripcion": "",
                "ruta_archivo": str(file_path),
                "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
            }
            dataframe = upsert_record(dataframe, record)

        dataframe = dataframe.sort_values(
            by=["categoria_gramatical", "subcategoria", "palabra", "variante"]
        ).reset_index(drop=True)
        save_database(dataframe)
        return dataframe


def count_continuous_pending() -> int:
    """Cuenta imagenes pendientes en la carpeta de ingesta continua."""
    create_directory_tree()
    return len(
        [
            path
            for path in ENTRADAS_CONTINUAS_PATH.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ]
    )


def _match_search_mode(value: str, needle: str, search_mode: str) -> bool:
    """Aplica el modo de busqueda sobre un texto normalizado."""
    if not needle:
        return True
    normalized_value = normalize_text(value)
    if search_mode == "starts_with":
        return normalized_value.startswith(needle)
    if search_mode == "ends_with":
        return normalized_value.endswith(needle)
    if search_mode == "exact":
        return normalized_value == needle
    return needle in normalized_value


def _parse_continuous_filename(file_path: Path) -> dict:
    """Lee metadatos desde el nombre del archivo.

    Formato:
    palabra__categoria__subcategoria__variante.png
    """
    parts = file_path.stem.split("__")
    if len(parts) < 4:
        raise ValueError(
            "Usa el formato palabra__categoria__subcategoria__variante.png "
            "por ejemplo comer__verbo__acciones_diarias__color.png"
        )
    palabra, categoria, subcategoria, variante = parts[:4]
    return {
        "palabra": palabra,
        "categoria_gramatical": categoria,
        "subcategoria": subcategoria,
        "variante": variante,
    }


def ingest_continuous_folder() -> dict:
    """Importa nuevos ficheros desde entradas_continuas/ y los reclasifica."""
    create_directory_tree()
    imported = []
    rejected = []

    for file_path in ENTRADAS_CONTINUAS_PATH.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        try:
            metadata = _parse_continuous_filename(file_path)
            target_path = crear_pictograma_desde_archivo(
                origen_archivo=str(file_path),
                palabra=metadata["palabra"],
                categoria_gramatical=metadata["categoria_gramatical"],
                subcategoria=metadata["subcategoria"],
                genero="",
                numero="",
                categoria_semantica="",
                descripcion="Importado desde ingesta continua",
                edad_recomendada="",
                dificultad="",
                variante=metadata["variante"],
            )
            shutil.move(str(file_path), str(ENTRADAS_PROCESADAS_PATH / file_path.name))
            imported.append(target_path)
        except Exception as exc:  # noqa: BLE001
            shutil.move(str(file_path), str(ENTRADAS_RECHAZADAS_PATH / file_path.name))
            rejected.append({"file": file_path.name, "error": str(exc)})

    if imported:
        scan_library()

    return {"imported": imported, "rejected": rejected}


def get_catalog(
    search: str = "",
    categoria: str = "",
    subcategoria: str = "",
    variante: str = "",
    search_mode: str = "contains",
) -> List[Dict[str, str]]:
    """Devuelve el catalogo filtrado como lista de registros."""
    dataframe = load_database().fillna("")

    if search:
        needle = normalize_text(search)
        dataframe = dataframe[
            dataframe["palabra"].astype(str).map(lambda value: _match_search_mode(value, needle, search_mode))
            | dataframe["descripcion"].astype(str).map(lambda value: _match_search_mode(value, needle, search_mode))
            | dataframe["categoria_semantica"].astype(str).map(lambda value: _match_search_mode(value, needle, search_mode))
        ]

    if categoria:
        dataframe = dataframe[dataframe["categoria_gramatical"] == categoria]
    if subcategoria:
        dataframe = dataframe[dataframe["subcategoria"] == subcategoria]
    if variante:
        dataframe = dataframe[dataframe["variante"] == normalize_variant(variante)]

    return dataframe.sort_values(by=["palabra", "variante"]).to_dict(orient="records")


def list_categories() -> Dict[str, List[str]]:
    """Expone la estructura de categorias para la interfaz web."""
    return {category: [display_subcategory(sub) for sub in subs] for category, subs in ESTRUCTURA.items()}


def prepare_demo_pictogram() -> Path | None:
    """Copia una imagen existente como demo y la registra en la base."""
    source_images = [
        path
        for path in ROOT_PATH.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not source_images:
        return None

    target_path = Path(
        crear_pictograma(
            palabra="comer",
            categoria_gramatical="verbo",
            subcategoria="acciones_diarias",
            genero="",
            numero="",
            categoria_semantica="rutina",
            descripcion="accion de ingerir alimentos",
            edad_recomendada="3+",
            dificultad="baja",
            variante=DEFAULT_VARIANT,
        )
    )

    if not target_path.exists():
        shutil.copy2(source_images[0], target_path)

    return target_path


def build_argument_parser() -> argparse.ArgumentParser:
    """CLI sencilla para inicializar, escanear o registrar pictogramas."""
    parser = argparse.ArgumentParser(description="Gestiona la biblioteca de pictogramas de araia.")
    parser.add_argument("--init", action="store_true", help="Crea la estructura y el Excel.")
    parser.add_argument("--scan", action="store_true", help="Escanea la biblioteca y actualiza el Excel.")
    parser.add_argument("--demo", action="store_true", help="Crea un pictograma de ejemplo llamado comer.")
    parser.add_argument("--palabra", help="Palabra del pictograma a registrar.")
    parser.add_argument("--categoria", help="Categoria gramatical del pictograma.")
    parser.add_argument("--subcategoria", default="", help="Subcategoria del pictograma.")
    parser.add_argument("--genero", default="", help="Genero gramatical.")
    parser.add_argument("--numero", default="", help="Numero gramatical.")
    parser.add_argument("--categoria-semantica", default="", help="Categoria semantica.")
    parser.add_argument("--descripcion", default="", help="Descripcion del pictograma.")
    parser.add_argument("--edad-recomendada", default="", help="Edad orientativa.")
    parser.add_argument("--dificultad", default="", help="Nivel de dificultad.")
    parser.add_argument("--variante", default=DEFAULT_VARIANT, help="Variante visual: blanco_y_negro o color.")
    parser.add_argument("--origen-archivo", default="", help="Ruta de una imagen para copiarla al catalogo.")
    return parser


def main() -> None:
    """Entrada de linea de comandos."""
    parser = build_argument_parser()
    args = parser.parse_args()

    create_directory_tree()
    initialize_excel()

    if args.palabra and args.categoria:
        if args.origen_archivo:
            path = crear_pictograma_desde_archivo(
                origen_archivo=args.origen_archivo,
                palabra=args.palabra,
                categoria_gramatical=args.categoria,
                subcategoria=args.subcategoria,
                genero=args.genero,
                numero=args.numero,
                categoria_semantica=args.categoria_semantica,
                descripcion=args.descripcion,
                edad_recomendada=args.edad_recomendada,
                dificultad=args.dificultad,
                variante=args.variante,
            )
        else:
            path = crear_pictograma(
                palabra=args.palabra,
                categoria_gramatical=args.categoria,
                subcategoria=args.subcategoria,
                genero=args.genero,
                numero=args.numero,
                categoria_semantica=args.categoria_semantica,
                descripcion=args.descripcion,
                edad_recomendada=args.edad_recomendada,
                dificultad=args.dificultad,
                variante=args.variante,
            )
        print(path)
        return

    if args.demo:
        demo_path = prepare_demo_pictogram()
        if demo_path:
            print(f"Demo creada en: {demo_path}")
        else:
            print("No se encontro ninguna imagen fuente para crear la demo.")

    if args.scan:
        dataframe = scan_library()
        print(f"Biblioteca sincronizada. Registros: {len(dataframe)}")
        return

    if args.init or not any(vars(args).values()):
        print(f"Estructura lista en: {ROOT_PATH}")
        print(f"Excel listo en: {EXCEL_PATH}")


if __name__ == "__main__":
    main()
