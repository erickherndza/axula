# Axula — Versión Modular

## Estructura del proyecto

```
elearning/
├── app.py                  ← Factory pattern (165 líneas)
├── core/
│   ├── __init__.py         ← Re-exporta componentes principales
│   ├── constants.py        ← ROLES, PLAN_ARTES, COLUMNAS_ESTUDIANTES, TABLAS, etc. (811 líneas)
│   ├── auth.py             ← Hash, decoradores, CSRF, roles, get_usuario (214 líneas)
│   ├── database.py         ← get_db, caché, migrar_bd, _seed_admin (233 líneas)
│   ├── helpers.py          ← 49 funciones auxiliares (1,564 líneas)
│   ├── ia.py               ← Cliente Groq, constructores de prompts (240 líneas)
│   ├── excel.py            ← Parsers Excel/boletín (305 líneas)
│   └── pdf.py              ← Generador PDF acuerdo (296 líneas)
├── routes/                 ← 16 Blueprints, 170 rutas
│   ├── __init__.py         ← Registro central de blueprints
│   ├── auth.py             ← Login, logout, SMTP, recovery (11 rutas)
│   ├── usuarios.py         ← CRUD usuarios, bulk (6 rutas)
│   ├── estudiantes.py      ← Perfiles, carga, ML, expediente, cuaderno (40 rutas)
│   ├── calificaciones.py   ← Notas, recuperaciones, boletín (9 rutas)
│   ├── asistencia.py       ← Registro, resumen, mensual (12 rutas)
│   ├── casos.py            ← Gestión de casos, acuerdos (13 rutas)
│   ├── firmas.py           ← Página de firma de acuerdos (1 ruta)
│   ├── reportes.py         ← CRUD reportes, export XLSX/PDF (8 rutas)
│   ├── notificaciones.py   ← Listado, conteo, SSE (7 rutas)
│   ├── calendario.py       ← Días, ICS, Google Calendar (9 rutas)
│   ├── portal_padres.py    ← Portal de padres/tutores (5 rutas)
│   ├── profesor.py         ← Portal profesor, perfil, búsqueda (8 rutas)
│   ├── planificacion.py    ← Planificación IA, ABP, DOCX (11 rutas)
│   ├── config.py           ← DB admin, auditoría, períodos (15 rutas)
│   ├── dashboard.py        ← Index, dashboard, coordinador (5 rutas)
│   └── asignaciones.py     ← Gestión de asignaciones (10 rutas)
├── templates/              ← Sin cambios
├── static/                 ← Sin cambios
└── database.db             ← Sin cambios
```

## Cómo instalar

### 1. Hacer backup del monolito
```bash
cd /Users/erickhernandez/elearning/
cp app.py app_monolito_backup.py
```

### 2. Copiar los archivos modulares
```bash
# Copiar core/ y routes/ al directorio del proyecto
cp -r core/ /Users/erickhernandez/elearning/core/
cp -r routes/ /Users/erickhernandez/elearning/routes/

# Reemplazar app.py con la versión modular
cp app.py /Users/erickhernandez/elearning/app.py
```

### 3. Verificar que funciona
```bash
cd /Users/erickhernandez/elearning/
python3 -c "from app import app; print(f'{len(app.blueprints)} blueprints, {len(list(app.url_map.iter_rules()))} rutas')"
# Debe imprimir: 16 blueprints, 171 rutas

# Arrancar el servidor
python3 app.py
```

### 4. Si algo falla — rollback inmediato
```bash
cp app_monolito_backup.py app.py
rm -rf core/ routes/
# Listo, vuelves al monolito funcional
```

## Cambios importantes

### url_for() en decoradores
Los decoradores `login_required`, `coord_required`, `admin_required`, `csrf_protected`
ahora usan `url_for("auth_bp.login_page")` en vez de `url_for("login_page")`.

Si tienes templates con `url_for("login_page")`, cámbialos a `url_for("auth_bp.login_page")`.

### Templates que usen url_for de rutas
Con blueprints, las funciones de ruta se referencian con prefijo:
- `url_for("login_page")` → `url_for("auth_bp.login_page")`
- `url_for("dashboard_clasico")` → `url_for("dashboard_bp.dashboard_clasico")`
- `url_for("perfil_estudiante", id=1)` → `url_for("estudiantes_bp.perfil_estudiante", id=1)`

## Estadísticas

| Métrica | Monolito | Modular |
|---------|----------|---------|
| Archivo principal | 15,066 líneas | 165 líneas |
| Archivos Python | 1 | 25 |
| Archivo más largo | 15,066 (app.py) | 3,359 (estudiantes.py) |
| Total líneas | 15,066 | ~14,300 |
| Rutas | 170 | 170 ✅ |
| Funciones | 257 | 257 ✅ |
