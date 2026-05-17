# ADR-005 — Reportes PDF con WeasyPrint (HTML → PDF)

**Estado:** Aceptado
**Fecha:** 2026-05-16

## Contexto

El reporte consolidado debe ser un PDF descargable que contenga
metadatos del caso, hallazgos por categoría, severidad, evidencia
estructurada, y auditoría de subtareas.

Opciones:

- **ReportLab**: control total, pero requiere posicionar cada elemento
  por coordenadas. Tedioso de mantener.
- **WeasyPrint (HTML+CSS → PDF)**: escribimos un template Jinja2
  con CSS estándar y dejamos que la librería maquete. Es lo que cualquier
  desarrollador web ya conoce.
- **Headless Chrome (Playwright)**: máxima fidelidad CSS pero pesa 250MB
  más en la imagen Docker y suma latencia.

## Decisión

**WeasyPrint** con un único template `report.html`. CSS limitado a las
features que WeasyPrint soporta bien (grid básico, tablas, colores).

## Consecuencias

**Positivas**
- Iteración rápida del template (es HTML/CSS).
- Reuso fácil del mismo template en la web si algún día se renderiza in-app.
- Imagen Docker sigue siendo razonable (~600 MB incluyendo Pango/Cairo).

**Negativas**
- WeasyPrint no soporta Flexbox completo ni JavaScript. Aceptable para
  reportes estructurados; cualquier complejidad nueva se resuelve con
  tablas + grid básico.
