# Pokédex API

![CI](https://github.com/Poke-con-toque/pokedex-api/actions/workflows/ci.yml/badge.svg)

API REST con FastAPI para gestionar una Pokédex personal: consulta Pokémon mediante [PokeAPI](https://pokeapi.co/), crea una colección privada, organiza equipos y descarga fichas y equipos en PDF.

> Práctica 1 · Módulo 2: APIs REST y Fundamentos de Integración · Sistemas de Información (UFV)

## Equipo

| Miembro | Usuario Git | Partes |
|---|---|---|
| Mario Linares | [@mariolinaresmerino-commits](https://github.com/mariolinaresmerino-commits) | Esqueleto y estructura base, autenticación JWT, CRUD de la Pokédex, estadísticas, exportación de la Pokédex (CSV y PDF), rate limiting y CORS, `SECURITY.md` y sus tests |
| Adrián Del Castillo | [@adriandczv](https://github.com/adriandczv) | CI, cliente de PokeAPI, logging, búsqueda y detalle, fichas PDF, equipos, exportación de equipos, API v2 y sus tests |

## Instalación

Se recomienda [uv](https://docs.astral.sh/uv/) y Python 3.12.

```bash
git clone https://github.com/Poke-con-toque/pokedex-api.git
cd pokedex-api
uv sync
cp .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia la clave generada en `SECRET_KEY` dentro de `.env`. En Windows, copia el archivo con `copy .env.example .env`.

También se pueden instalar las dependencias con `pip install -r requirements.txt`.

## Configuración

| Variable | Descripción | Valor local |
|---|---|---|
| `SECRET_KEY` | Clave privada para firmar los JWT; genera una diferente para cada entorno | Obligatoria |
| `DATABASE_URL` | URL de la base de datos SQLModel | `sqlite:///./pokedex.db` |
| `CORS_ORIGINS` | Orígenes web permitidos, como lista JSON | `["http://localhost:5173"]` |
| `POKEAPI_BASE_URL` | URL base de la PokeAPI | `https://pokeapi.co/api/v2` |
| `POKEAPI_TIMEOUT` | Tiempo máximo de espera para PokeAPI, en segundos | `5` |
| `POKEAPI_FALLBACK` | Activa datos locales de reserva si PokeAPI no responde | `false` |
| `ALGORITHM` | Algoritmo de firma JWT | `HS256` por defecto |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token de acceso | `1440` por defecto |

No subas el archivo `.env` ni claves reales al repositorio.

## Ejecución

```bash
uv run uvicorn app.main:app --reload
```

- API local: http://localhost:8000
- Estado: http://localhost:8000/health
- Documentación interactiva: http://localhost:8000/docs

La base de datos se crea al arrancar la aplicación.

## Pruebas

```bash
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
```

GitHub Actions ejecuta Ruff y las pruebas con cobertura mínima del 80 % en los PR y pushes a `main` y `develop`.

Las pruebas no salen a Internet: la PokeAPI se simula con `respx` (`tests/pokeapi_mocks.py`) y cada test usa una base de datos SQLite en memoria. La suite tiene más de 130 pruebas y una cobertura del 99 %.

## Endpoints principales

Las rutas de la API requieren un token Bearer salvo registro, login y `/health`.

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/v1/auth/register` | Crear cuenta |
| POST | `/api/v1/auth/login` | Obtener JWT con formulario OAuth2 |
| GET | `/api/v1/auth/me` | Consultar la cuenta autenticada |
| GET | `/api/v1/pokemon/search` | Buscar Pokémon; admite nombre parcial, límite y desplazamiento |
| GET | `/api/v1/pokemon/{id_or_name}` | Consultar datos, estadísticas, habilidades y sprites |
| GET | `/api/v1/pokemon/{id_or_name}/card` | Descargar ficha de Pokémon en PDF |
| POST | `/api/v1/pokedex` | Añadir un Pokémon a la colección |
| GET | `/api/v1/pokedex` | Consultar la colección con filtros, orden y paginación |
| GET | `/api/v1/pokedex/stats` | Total, capturados, favoritos, porcentaje capturado, tipo más común y racha de capturas |
| GET | `/api/v1/pokedex/export` | Descargar la colección en CSV o PDF (`format=csv\|pdf`, filtros `captured` y `favorite`) |
| GET | `/api/v1/pokedex/{entry_id}` | Consultar una entrada |
| PATCH | `/api/v1/pokedex/{entry_id}` | Actualizar apodo, captura, fecha, notas o favorito |
| DELETE | `/api/v1/pokedex/{entry_id}` | Quitar una entrada |
| POST / GET | `/api/v1/teams` | Crear y listar equipos de batalla |
| GET / PUT / DELETE | `/api/v1/teams/{team_id}` | Consultar, actualizar o borrar un equipo |
| GET | `/api/v1/teams/{team_id}/export` | Descargar un equipo en PDF |
| GET | `/api/v2/pokedex` | Consultar la colección incluyendo cadenas evolutivas |

## Flujo de trabajo

- `main` contiene la versión estable y entregable.
- `develop` integra las funcionalidades.
- Cada funcionalidad se trabaja en `features/<nombre>` y se integra en `develop` mediante un pull request revisado y aprobado por el otro miembro, con el CI en verde.
- Las correcciones de algo ya integrado van en `fix/<nombre>`.
- Los commits siguen *Conventional Commits* (`feat`, `fix`, `test`, `docs`, `refactor`, `chore`).
- Cada funcionalidad tiene su issue, organizada en el tablero de [GitHub Projects](https://github.com/orgs/Poke-con-toque/projects); el PR la cierra con `Closes #N`.
- La versión entregada es la etiqueta `v1.0.0` de `main`.
- El despliegue público en Render es opcional y aún no está configurado.

## Decisiones de Diseño

### Rate limiting

| Tipo de endpoint | Límite por IP | Endpoints |
|---|---|---|
| Registro | 5/hora | `POST /auth/register` |
| Login | 10/minuto | `POST /auth/login` |
| Llaman a la PokeAPI | 30/minuto | `/pokemon/search`, `/pokemon/{id}`, `/pokemon/{id}/card`, `POST /pokedex`, `/teams/{id}/export`, `/api/v2/pokedex` |
| Resto de endpoints autenticados | 100/minuto | `/auth/me`, CRUD de la Pokédex, estadísticas, exportación y equipos |
| Sin límite | — | `/health` (monitorización) |

**¿Por qué límites distintos?** Cada tipo de endpoint tiene un coste y un riesgo diferentes. El registro y el login son públicos y son el objetivo de la fuerza bruta y de la creación masiva de cuentas, así que son los más estrictos. Los endpoints que llaman a la PokeAPI generan peticiones hacia un servicio externo y gratuito que también nos limita a nosotros: si un cliente abusa, nos pueden bloquear a todos. El resto solo consulta nuestra base de datos y es barato, así que admite un uso normal de una aplicación web.

**¿Cómo protege la API?** Frena los ataques de diccionario contra el login, el spam de cuentas, el abuso que podría agotar la cuota de la PokeAPI y los picos de tráfico que dejarían la API sin servicio para el resto (denegación de servicio).

**¿Qué pasa si un usuario excede el límite?** La petición no llega al endpoint: la API responde `429 Too Many Requests` con el mismo formato que el resto de errores (`{"detail": "Demasiadas peticiones: límite de 10 per 1 minute"}`) y deja un aviso en el log con el método, la ruta y la IP. Cuando pasa la ventana de tiempo, el cliente puede volver a hacer peticiones.

Los límites se definen en `app/limits.py` con `slowapi` y cada endpoint declara el suyo con `@limiter.limit`. No se usa `default_limits`, porque con FastAPI 0.148 el middleware de `slowapi` no localiza las rutas de los routers incluidos y esos límites no se aplicarían; un test comprueba que ningún endpoint se queda sin límite.

### Versionado

Las rutas llevan un prefijo explícito: `/api/v1` o `/api/v2`. Se abre una versión nueva cuando un cambio incompatible afecta las respuestas o el comportamiento de clientes existentes. La v2 añade, en paralelo a v1, `GET /api/v2/pokedex` con los mismos filtros y la cadena evolutiva; los demás endpoints siguen disponibles bajo `/api/v1`. La v1 seguirá disponible durante la transición; antes de retirarla se anunciarán la fecha y el periodo de migración, junto con cabeceras `Deprecation` y `Sunset`.

### Otras decisiones

- Cada cuenta solo puede consultar o modificar su propia colección y sus equipos.
- Se sigue la estructura de la práctica guiada de clase: `uv` para las dependencias (con `requirements.txt` generado para el CI), contratos Base → Table → Create / Read / Update en `models.py` y dependencias `SessionDep`, `CurrentUser` y `ServicioPokeAPI`.
- Las contraseñas usan `bcrypt` directamente en lugar de `passlib`, que no se mantiene y falla con `bcrypt` 5.
- Se usa SQLModel para validar datos y parametrizar consultas; los parámetros de orden se traducen a columnas y nunca se insertan en el SQL.
- `completion_percentage` es el porcentaje de la Pokédex del usuario que ya está capturado. `most_common_type` se calcula con los tipos que se guardan al añadir cada Pokémon (si hay empate, el primero alfabéticamente). `capture_streak_days` cuenta los días seguidos con alguna captura hasta hoy, o hasta ayer si hoy aún no hay ninguna.
- Los PDF se generan con `fpdf2`. Los sprites se descargan de forma asíncrona y en paralelo; si fallan, el PDF se genera sin imagen.
- Las respuestas de PokeAPI se reducen a los campos que consume la aplicación y se mantienen en caché en memoria.
- La integración continua usa datos de prueba y mocks; no necesita llamar a PokeAPI.

## Decisiones de Seguridad

- Las contraseñas se almacenan con hash bcrypt; se exige un mínimo de longitud, una mayúscula y un número.
- Los JWT se firman con una clave de entorno y caducan tras 24 horas por defecto.
- El login devuelve el mismo mensaje si falla el usuario o la contraseña.
- Las rutas privadas responden con 401 si el token falta, es inválido o ha caducado. Los recursos ajenos responden 404.
- CORS usa la lista configurada en `CORS_ORIGINS` y limita métodos y cabeceras permitidos.
- Rate limiting diferenciado por tipo de endpoint (ver «Decisiones de Diseño»).
- La exportación CSV neutraliza las celdas que empiezan por `=`, `+`, `-` o `@` para evitar la inyección de fórmulas en Excel.
- Los logs de errores de validación no guardan los valores recibidos, para no registrar contraseñas.

El detalle completo, con la revisión del OWASP API Security Top 10, está en [SECURITY.md](SECURITY.md).
- Las claves y la URL de base de datos se configuran en variables de entorno.

## Mejoras Futuras

- Refresh tokens de 7 días, para no tener que volver a iniciar sesión cada 24 horas.
- Guardar los contadores del rate limiting en Redis, para que se compartan entre varias instancias y no se reinicien al reiniciar la API.
- Migraciones de base de datos con Alembic, recuperación de contraseña y despliegue en Render.
- Enviar las cabeceras `Deprecation` y `Sunset` en v1 cuando se planifique su retirada.
- Mantener las dependencias y reglas de acceso actualizadas.

En producción se debe usar HTTPS para proteger las credenciales, los JWT y los datos durante el transporte.
