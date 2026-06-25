# Guion demo — YIVTOL S-ZERO + AyronOne

Base demo local: `postgres://demo:demo@demo-db:5432/yivtol_demo`

Re-seed: `python manage.py seed_yivtol_demo --force`

Si cambiaste el nombre de la base, recreá el volumen: `docker compose down -v && docker compose up -d`

## Preguntas sugeridas

1. **Estado del Lote 7**
   *Dame el estado del lote 7 esta semana*
   → Tabla con NDVI, NDRE, estrés hídrico y alerta de Zona Norte (42 ha).

2. **Rodeo del Corral 5**
   *Dame el estado del rodeo del corral 5*
   → Tabla de animales con peso, BCS, temperatura y alertas activas.

3. **NDRE histórico Lote Norte**
   *Comparame el NDRE de abril con el de mayo en el lote norte*
   → Gráfico de líneas con dos vuelos YIVTOL.

4. **Alertas de estrés hídrico**
   *¿Qué lotes tienen alertas activas de estrés hídrico?*
   → Tabla desde `agricola_alertas` con ha afectadas y recomendación.

5. **Animales en alerta sanitaria**
   *¿Cuántos animales en el corral 5 tienen temperatura sobre el promedio del lote?*
   → Tabla filtrada por `estado = 'alerta'` o delta térmico.

6. **Ventana de venta Corral 3**
   *¿Cuántos animales del corral 3 superaron 480 kg?*
   → Conteo + alerta de comercialización.

7. **Rotación de pasturas**
   *¿Cuál es el plan de rotación del potrero A?*
   → Biomasa 38%, rotar en 7 días.

8. **Ranking de lotes**
   *Ranking de performance de todos los lotes por rinde proyectado*
   → Gráfico de barras inter-lote.

9. **Dashboard ejecutivo agropecuario**
   *Genera un dashboard ejecutivo con KPIs de lotes y corrales, filtros y export PDF*
   → `publish_html_artifact` (skill html-reports).

10. **Reporte prendario / banco**
    *Generame el reporte de rodeo para el banco*
    → Documento con conteo certificado, peso promedio, hash del vuelo RTK.

## Establecimientos demo

| Establecimiento | Tipo | Ubicación |
|-----------------|------|-----------|
| Estancia Cliente Cero | Campo (8 lotes, ~4.200 ha) | Buenos Aires |
| Feedlot Cliente Cero | Feedlot (~3.000 cab.) | Buenos Aires |

## Fuentes simuladas

| Dominio | Prefijo tablas | Contenido |
|---------|----------------|-----------|
| Vuelos YIVTOL | `yivtol_*` | Operaciones aéreas, hash certificado, cobertura |
| Agricultura | `agricola_*` | Lotes, mediciones NDVI/NDRE, zonas, alertas |
| Ganadería | `ganaderia_*` | Corrales, animales, potreros, alertas |
