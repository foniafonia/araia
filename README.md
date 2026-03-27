# araia pictogramas

Proyecto Python para construir y mantener una biblioteca propia de pictogramas, con gestor local en Python y visualizador web publico en GitHub Pages.

## Archivos principales

- Gestor principal: `scripts/gestor_pictogramas.py`
- Exportador web: `scripts/exportar_catalogo_web.py`
- Visualizador web: `index.html`
- Biblioteca de imagenes publicas: `pictogramas/`

## Dependencias

```bash
python3 -m pip install pandas openpyxl flask
```

## Uso local

```bash
cd /ruta/a/araia
python3 scripts/gestor_pictogramas.py --init
python3 scripts/gestor_pictogramas.py --scan
python3 app.py
```

## Publicacion web

El visualizador estatico usa:

- `index.html`
- `static/pages.js`
- `static/pages.css`
- `catalogo_web.json`

Para regenerar el catalogo publico desde el Excel local:

```bash
python3 scripts/exportar_catalogo_web.py
```

## Privacidad

El repositorio publico no debe incluir:

- archivos de estado de usuarios
- backups locales
- excels con rutas absolutas
- exportaciones descartadas
- colas de trabajo privadas

Esos datos se generan y se mantienen solo en local.
