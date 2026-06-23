# Guion demo — Mexar Pharma

Base demo local: `postgres://demo:demo@demo-db:5432/mexar_demo`

Re-seed: `python manage.py seed_mexar_demo --force`

## Preguntas sugeridas

1. **Ventas por área terapéutica (trimestre actual)**  
   *¿Cómo van las ventas por área terapéutica este trimestre?*  
   → Gráfico de barras (oncología y diabetes deberían destacar).

2. **Top productos oncología**  
   *Top productos de oncología por ingreso: Asgen, Iriaspe, Kebiras, Degehn*  
   → Tabla con marcas del catálogo real.

3. **Diabetes: Argliptin-D vs Bitam**  
   *Compara ventas de Argliptin-D vs Bitam en diabetes*  
   → Gráfico comparativo por molécula.

4. **Regional Jalisco vs CDMX**  
   *Compara ingresos Jalisco vs Ciudad de México en los últimos 12 meses*  
   → Gráfico de líneas.

5. **Pipeline de licenciamiento**  
   *¿Qué oportunidades de licenciamiento de Gemcitabina o Docetaxel cierran en los próximos 60 días?*  
   → Tabla CRM.

6. **Dashboard ejecutivo**  
   *Genera un dashboard ejecutivo del catálogo Mexar por área terapéutica con KPIs, filtros y export PDF*  
   → `publish_html_artifact` (skill html-reports).

## Catálogo

18 SKUs del [catálogo Mexar](https://www.mexarpharma.com/catalogo): Hyperlub 5, HyaluFresh, Argliptin-D, Bitam, Selencor, Fibcorif, Kamedix, Brylupa, Degehn, Asgen, Iriaspe, Kebiras, Mocedam, Dacrolem, Vadismed, Drastep, Varpharm.

## Fuentes simuladas

| Dominio | Prefijo tablas | Contenido |
|---------|----------------|-----------|
| ERP Comercial | `comercial_*` | Productos, pedidos, instituciones, inventario |
| CRM Licenciamiento | `crm_*` | Cuentas, contactos, oportunidades, actividades |
