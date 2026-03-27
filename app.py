#!/usr/bin/env python3
"""Aplicacion web para explorar, guardar y jugar con la biblioteca de pictogramas."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, make_response, redirect, render_template, request, send_file, url_for

from scripts.gestor_pictogramas import (
    ROOT_PATH,
    ENTRADAS_CONTINUAS_PATH,
    count_continuous_pending,
    crear_pictograma_desde_archivo,
    create_directory_tree,
    get_catalog,
    ingest_continuous_folder,
    list_categories,
    normalize_variant,
    scan_library,
    slugify,
)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

PROFILES_PATH = ROOT_PATH / "base_datos" / "biblioteca_digital_local.json"
REQUESTS_PATH = ROOT_PATH / "base_datos" / "solicitudes_usuarios_local.json"
FEEDBACK_PATH = ROOT_PATH / "base_datos" / "comentarios_usuarios_local.json"
DEFAULT_PROFILE = "general"
ALPHABET = [chr(code) for code in range(ord("A"), ord("Z") + 1)]


def normalize_profile_name(value: str) -> str:
    """Normaliza nombres de perfil para usarlos de forma segura."""
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    return cleaned[:40] or DEFAULT_PROFILE


def ensure_app_files() -> None:
    """Asegura estructura base y archivo de perfiles."""
    create_directory_tree()
    if not PROFILES_PATH.exists():
        PROFILES_PATH.write_text(
            json.dumps({"active_profile": DEFAULT_PROFILE, "profiles": {DEFAULT_PROFILE: {"paths": []}}}, indent=2),
            encoding="utf-8",
        )
    if not REQUESTS_PATH.exists():
        REQUESTS_PATH.write_text(json.dumps({"requests": []}, indent=2), encoding="utf-8")
    if not FEEDBACK_PATH.exists():
        FEEDBACK_PATH.write_text(json.dumps({"feedback": []}, indent=2), encoding="utf-8")


def safe_root_path(raw_path: str) -> Path | None:
    """Valida que la ruta pertenezca al proyecto y exista."""
    if not raw_path:
        return None
    target = Path(raw_path).resolve()
    root = ROOT_PATH.resolve()
    if not str(target).startswith(str(root)) or not target.exists():
        return None
    return target


def load_profiles_data() -> dict:
    """Carga la estructura de perfiles y corrige formatos antiguos."""
    ensure_app_files()
    data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))

    if "profiles" not in data:
        legacy_paths = data.get("paths", [])
        data = {"active_profile": DEFAULT_PROFILE, "profiles": {DEFAULT_PROFILE: {"paths": legacy_paths}}}

    if not data["profiles"]:
        data["profiles"] = {DEFAULT_PROFILE: {"paths": []}}

    if "active_profile" not in data or data["active_profile"] not in data["profiles"]:
        data["active_profile"] = next(iter(data["profiles"]))

    for profile_name, payload in data["profiles"].items():
        payload.setdefault("paths", [])
        payload["paths"] = [path for path in payload["paths"] if safe_root_path(path)]

    return data


def save_profiles_data(data: dict) -> None:
    """Guarda la estructura de perfiles."""
    PROFILES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_active_profile(data: dict | None = None) -> str:
    """Resuelve el perfil activo actual."""
    payload = data or load_profiles_data()
    selected = normalize_profile_name(request.cookies.get("araia_profile", payload["active_profile"]))
    if selected not in payload["profiles"]:
        selected = payload["active_profile"]
    return selected


def get_profile_names(data: dict | None = None) -> list[str]:
    """Lista de perfiles disponibles."""
    payload = data or load_profiles_data()
    return sorted(payload["profiles"].keys())


def load_digital_library_paths(profile_name: str | None = None) -> list[str]:
    """Carga rutas guardadas en la biblioteca digital de un perfil."""
    payload = load_profiles_data()
    active_profile = profile_name or get_active_profile(payload)
    return payload["profiles"].get(active_profile, {}).get("paths", [])


def save_digital_library_paths(paths: list[str], profile_name: str | None = None) -> None:
    """Guarda rutas sin duplicados para un perfil."""
    payload = load_profiles_data()
    active_profile = profile_name or get_active_profile(payload)
    payload["profiles"].setdefault(active_profile, {"paths": []})

    unique_paths = []
    seen = set()
    for path in paths:
        if path not in seen and safe_root_path(path):
            unique_paths.append(path)
            seen.add(path)

    payload["profiles"][active_profile]["paths"] = unique_paths
    payload["active_profile"] = active_profile
    save_profiles_data(payload)


def build_filters() -> dict:
    """Recoge filtros de la request actual."""
    return {
        "search": request.args.get("q", "").strip(),
        "search_mode": request.args.get("search_mode", "contains").strip() or "contains",
        "letter": request.args.get("letter", "").strip().upper(),
        "categoria": request.args.get("categoria", "").strip(),
        "subcategoria": request.args.get("subcategoria", "").strip(),
        "variante": request.args.get("variante", "").strip(),
    }


def load_requests_data() -> dict:
    """Carga solicitudes de usuarios."""
    ensure_app_files()
    data = json.loads(REQUESTS_PATH.read_text(encoding="utf-8"))
    data.setdefault("requests", [])
    return data


def save_requests_data(data: dict) -> None:
    """Guarda solicitudes de usuarios."""
    REQUESTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_feedback_data() -> dict:
    """Carga comentarios y sugerencias."""
    ensure_app_files()
    data = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
    data.setdefault("feedback", [])
    return data


def save_feedback_data(data: dict) -> None:
    """Guarda comentarios y sugerencias."""
    FEEDBACK_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def recent_records(limit: int = 8) -> list[dict]:
    """Devuelve los pictogramas más recientes por fecha de creación."""
    records = get_catalog()
    return sorted(records, key=lambda record: record.get("fecha_creacion", ""), reverse=True)[:limit]


def filter_records_by_letter(records: list[dict], letter: str, search_mode: str) -> list[dict]:
    """Aplica el filtro alfabético usando el modo de búsqueda seleccionado."""
    if not letter:
        return records
    needle = letter.lower()
    filtered = []
    for record in records:
        word = str(record.get("palabra", "")).lower()
        if search_mode == "starts_with" and word.startswith(needle):
            filtered.append(record)
        elif search_mode == "ends_with" and word.endswith(needle):
            filtered.append(record)
        elif search_mode == "exact" and word == needle:
            filtered.append(record)
        elif search_mode == "contains" and needle in word:
            filtered.append(record)
    return filtered


def get_requests_with_priority() -> list[dict]:
    """Ordena solicitudes por prioridad social y recencia."""
    data = load_requests_data()
    feedback = load_feedback_data()["feedback"]
    comments_per_word = {}
    for item in feedback:
        palabra = item.get("palabra", "").strip().lower()
        if palabra:
            comments_per_word[palabra] = comments_per_word.get(palabra, 0) + 1

    requests_list = []
    for item in data["requests"]:
        palabra_key = item.get("palabra", "").strip().lower()
        enriched = dict(item)
        enriched["comment_count"] = comments_per_word.get(palabra_key, 0)
        enriched["priority_score"] = int(item.get("votes", 0)) + int(item.get("requests", 0)) + enriched["comment_count"]
        requests_list.append(enriched)

    return sorted(
        requests_list,
        key=lambda item: (item["priority_score"], item.get("updated_at", ""), item.get("created_at", "")),
        reverse=True,
    )


def daily_batch(limit: int = 2) -> list[dict]:
    """Lote diario recomendado para producción controlada."""
    pending = [item for item in get_requests_with_priority() if item.get("status", "pending") == "pending"]
    return pending[:limit]


def latest_feedback(limit: int = 10) -> list[dict]:
    """Comentarios recientes de la comunidad."""
    items = load_feedback_data()["feedback"]
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]


def enrich_records(records: list[dict], library_paths: list[str]) -> list[dict]:
    """Marca si cada pictograma ya esta guardado en biblioteca digital."""
    saved = set(library_paths)
    enriched = []
    for record in records:
        enriched_record = dict(record)
        enriched_record["in_library"] = record.get("ruta_archivo", "") in saved
        enriched.append(enriched_record)
    return enriched


def get_digital_library_records(profile_name: str | None = None) -> list[dict]:
    """Devuelve registros guardados en la biblioteca digital del perfil activo."""
    saved_paths = load_digital_library_paths(profile_name)
    all_records = {record["ruta_archivo"]: record for record in get_catalog()}
    records = [all_records[path] for path in saved_paths if path in all_records]
    return enrich_records(records, saved_paths)


def build_oca_cells(records: list[dict], total_cells: int = 24) -> list[dict]:
    """Genera tablero repitiendo los pictogramas seleccionados."""
    if not records:
        return []
    return [
        {
            "number": index + 1,
            "palabra": records[index % len(records)]["palabra"],
            "ruta_archivo": records[index % len(records)]["ruta_archivo"],
            "variante": records[index % len(records)].get("variante", ""),
        }
        for index in range(total_cells)
    ]


def render_with_profile(template_name: str, **context):
    """Inyecta estado de perfiles en todas las vistas principales."""
    payload = load_profiles_data()
    active_profile = get_active_profile(payload)
    return render_template(
        template_name,
        active_profile=active_profile,
        profiles=get_profile_names(payload),
        **context,
    )


@app.route("/")
def home():
    """Landing principal estilo buscador/catalogo."""
    ensure_app_files()
    scan_library()
    filters = build_filters()
    active_profile = get_active_profile()
    library_paths = load_digital_library_paths(active_profile)
    catalog_filters = {key: value for key, value in filters.items() if key != "letter"}
    records = enrich_records(get_catalog(**catalog_filters), library_paths)
    records = filter_records_by_letter(records, filters["letter"], filters["search_mode"])
    structure = list_categories()
    stats = {
        "total": len(records),
        "categorias": len([key for key in structure.keys() if key]),
        "variantes": len({record.get("variante", "") for record in records if record.get("variante", "")}),
        "guardados": len(library_paths),
        "pendientes": count_continuous_pending(),
    }
    return render_with_profile(
        "index.html",
        alphabet=ALPHABET,
        records=records,
        recent_records=enrich_records(recent_records(), library_paths),
        requests=get_requests_with_priority()[:12],
        daily_batch=daily_batch(),
        feedback_items=latest_feedback(),
        filters=filters,
        structure=structure,
        stats=stats,
        project_root=str(ROOT_PATH),
        continuous_folder=str(ENTRADAS_CONTINUAS_PATH),
    )


@app.route("/biblioteca-digital")
def digital_library():
    """Vista de la biblioteca digital guardada por el usuario."""
    ensure_app_files()
    scan_library()
    active_profile = get_active_profile()
    records = get_digital_library_records(active_profile)
    return render_with_profile("digital_library.html", records=records, total=len(records))


@app.route("/oca")
def oca():
    """Tablero interactivo construido con pictogramas seleccionados."""
    ensure_app_files()
    scan_library()
    active_profile = get_active_profile()
    selected_paths = request.args.getlist("selected_paths")
    player_one = request.args.get("player_one", "").strip() or "Jugador 1"
    player_two = request.args.get("player_two", "").strip() or "Jugador 2"
    base_records = get_digital_library_records(active_profile)
    indexed = {record["ruta_archivo"]: record for record in base_records}

    if selected_paths:
        selected_records = [indexed[path] for path in selected_paths if path in indexed]
    else:
        selected_records = base_records

    cells = build_oca_cells(selected_records)
    return render_with_profile(
        "oca.html",
        records=selected_records,
        cells=cells,
        player_one=player_one,
        player_two=player_two,
    )


@app.route("/api/pictograms")
def pictograms_api():
    """API JSON para futuras automatizaciones o interfaz JS."""
    ensure_app_files()
    scan_library()
    filters = build_filters()
    catalog_filters = {key: value for key, value in filters.items() if key != "letter"}
    records = get_catalog(**catalog_filters)
    records = filter_records_by_letter(records, filters["letter"], filters["search_mode"])
    return jsonify(records)


@app.route("/requests/add", methods=["POST"])
def add_request():
    """Registra o acumula una solicitud de pictograma."""
    data = load_requests_data()
    now = datetime.now().isoformat(timespec="seconds")
    palabra = request.form.get("palabra", "").strip()
    categoria = request.form.get("categoria_gramatical", "").strip()
    subcategoria = request.form.get("subcategoria", "").strip()
    detalle = request.form.get("detalle", "").strip()
    profile = get_active_profile()

    existing = next(
        (
            item
            for item in data["requests"]
            if item.get("palabra", "").strip().lower() == palabra.lower()
            and item.get("categoria_gramatical", "") == categoria
            and item.get("subcategoria", "") == subcategoria
        ),
        None,
    )
    if existing:
        existing["requests"] = int(existing.get("requests", 1)) + 1
        existing["votes"] = int(existing.get("votes", 0)) + 1
        existing["updated_at"] = now
        if detalle:
            existing["detalle"] = detalle
    else:
        data["requests"].append(
            {
                "id": slugify(f"{palabra}_{categoria}_{subcategoria}_{now}"),
                "palabra": palabra,
                "categoria_gramatical": categoria,
                "subcategoria": subcategoria,
                "detalle": detalle,
                "profile": profile,
                "requests": 1,
                "votes": 1,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }
        )
    save_requests_data(data)
    return redirect(request.referrer or url_for("home"))


@app.route("/requests/vote", methods=["POST"])
def vote_request():
    """Sube prioridad de una solicitud."""
    data = load_requests_data()
    request_id = request.form.get("request_id", "").strip()
    for item in data["requests"]:
        if item.get("id") == request_id:
            item["votes"] = int(item.get("votes", 0)) + 1
            item["updated_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_requests_data(data)
    return redirect(request.referrer or url_for("home"))


@app.route("/feedback/add", methods=["POST"])
def add_feedback():
    """Guarda opiniones, faltas, sugerencias o comentarios."""
    data = load_feedback_data()
    data["feedback"].append(
        {
            "id": slugify(datetime.now().isoformat(timespec="seconds")),
            "profile": get_active_profile(),
            "tipo": request.form.get("tipo", "sugerencia").strip(),
            "palabra": request.form.get("palabra", "").strip(),
            "path": request.form.get("path", "").strip(),
            "texto": request.form.get("texto", "").strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_feedback_data(data)
    return redirect(request.referrer or url_for("home"))


@app.route("/profiles/select", methods=["POST"])
def select_profile():
    """Selecciona el perfil activo para la experiencia web."""
    payload = load_profiles_data()
    profile_name = normalize_profile_name(request.form.get("profile_name", ""))
    if profile_name not in payload["profiles"]:
        profile_name = payload["active_profile"]
    payload["active_profile"] = profile_name
    save_profiles_data(payload)
    response = make_response(redirect(request.referrer or url_for("home")))
    response.set_cookie("araia_profile", profile_name, max_age=60 * 60 * 24 * 365)
    return response


@app.route("/profiles/create", methods=["POST"])
def create_profile():
    """Crea un perfil nuevo para separar bibliotecas digitales."""
    payload = load_profiles_data()
    profile_name = normalize_profile_name(request.form.get("new_profile_name", ""))
    payload["profiles"].setdefault(profile_name, {"paths": []})
    payload["active_profile"] = profile_name
    save_profiles_data(payload)
    response = make_response(redirect(request.referrer or url_for("home")))
    response.set_cookie("araia_profile", profile_name, max_age=60 * 60 * 24 * 365)
    return response


@app.route("/media")
def media():
    """Sirve imagenes del catalogo por ruta absoluta controlada."""
    target = safe_root_path(request.args.get("path", ""))
    if target is None:
        return ("Archivo no encontrado", 404)
    return send_file(target)


@app.route("/download")
def download():
    """Descarga directa del pictograma al ordenador."""
    target = safe_root_path(request.args.get("path", ""))
    if target is None:
        return ("Archivo no encontrado", 404)
    return send_file(target, as_attachment=True, download_name=target.name)


@app.route("/digital-library/add", methods=["POST"])
def add_to_library():
    """Guarda un pictograma en la biblioteca digital del perfil activo."""
    target = safe_root_path(request.form.get("path", ""))
    if target is None:
        return ("Archivo no encontrado", 404)

    active_profile = get_active_profile()
    paths = load_digital_library_paths(active_profile)
    if str(target) not in paths:
        paths.append(str(target))
        save_digital_library_paths(paths, active_profile)
    return redirect(request.referrer or url_for("home"))


@app.route("/digital-library/remove", methods=["POST"])
def remove_from_library():
    """Elimina un pictograma de la biblioteca digital del perfil activo."""
    target = safe_root_path(request.form.get("path", ""))
    if target is None:
        return ("Archivo no encontrado", 404)

    active_profile = get_active_profile()
    paths = [path for path in load_digital_library_paths(active_profile) if path != str(target)]
    save_digital_library_paths(paths, active_profile)
    return redirect(request.referrer or url_for("digital_library"))


@app.route("/scan", methods=["POST"])
def scan():
    """Lanza un escaneo manual desde la interfaz."""
    scan_library()
    return redirect(url_for("home"))


@app.route("/continuous-import", methods=["POST"])
def continuous_import():
    """Procesa la carpeta de ingesta continua y sube los pictos nuevos."""
    ingest_continuous_folder()
    return redirect(url_for("home"))


@app.route("/create", methods=["POST"])
def create():
    """Crea un pictograma a partir de un archivo subido desde la landing."""
    upload = request.files.get("archivo")
    if upload is None or upload.filename == "":
        return ("Falta la imagen del pictograma", 400)

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.filename).suffix) as tmp_file:
        upload.save(tmp_file.name)
        temp_path = tmp_file.name

    try:
        crear_pictograma_desde_archivo(
            origen_archivo=temp_path,
            palabra=request.form.get("palabra", ""),
            categoria_gramatical=request.form.get("categoria_gramatical", ""),
            subcategoria=request.form.get("subcategoria", ""),
            genero=request.form.get("genero", ""),
            numero=request.form.get("numero", ""),
            categoria_semantica=request.form.get("categoria_semantica", ""),
            descripcion=request.form.get("descripcion", ""),
            edad_recomendada=request.form.get("edad_recomendada", ""),
            dificultad=request.form.get("dificultad", ""),
            variante=normalize_variant(request.form.get("variante", "")),
        )
        scan_library()
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return redirect(url_for("home"))


if __name__ == "__main__":
    ensure_app_files()
    app.run(debug=False, host="127.0.0.1", port=5055)
