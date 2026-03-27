# Automatizacion 100 pictos diarios

Estado actual:
- `araia` ya clasifica, registra y publica pictogramas automaticamente.
- Falta conectar un generador de imagen IA para crear pictos originales sin archivo fuente.

Pipeline preparado:
1. Cola diaria en `base_datos/lote_generacion_diaria.csv`
2. Entrada automatica en `entradas_continuas/`
3. Clasificacion y subida a la web con `Procesar ingesta continua`

Siguiente paso tecnico:
- conectar OpenAI o Gemini para generar PNG originales
- escribir cada PNG con nombre `palabra__categoria__subcategoria__variante.png`
- moverlo a `entradas_continuas/`
- procesar la ingesta y actualizar Excel/web

Objetivo operativo:
- 100 pictogramas diarios
- revisados por lote
- clasificados en biblioteca y visibles en la web
