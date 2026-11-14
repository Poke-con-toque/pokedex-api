# Pokédex API

![CI](https://github.com/Poke-con-toque/pokedex-api/actions/workflows/ci.yml/badge.svg)

API REST con FastAPI para gestionar una Pokédex personal: consulta Pokémon mediante [PokeAPI](https://pokeapi.co/), crea una colección privada, organiza equipos y descarga fichas y equipos en PDF.

> Práctica 1 · Módulo 2: APIs REST y Fundamentos de Integración · Sistemas de Información (UFV)

## Equipo

| Miembro | Usuario Git | Partes |
|---|---|---|
| Mario Linares | [@mariolinaresmerino-commits](https://github.com/mariolinaresmerino-commits) | Estructura, autenticación JWT, CRUD y estadísticas de Pokédex, cliente PokeAPI y configuración de seguridad |
| Adrián Del Castillo | [@adriandczv](https://github.com/adriandczv) | CI, logging, búsqueda y detalle, fichas PDF, equipos, exportación de equipos y API v2 |

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

## Endpoints principales

Las rutas de la API requieren un token Bearer salvo registro, login y `/health).

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
| GET | `/api/v1/pokedex/stats` | Ver estadísticas básicas de la colección |
| PATCH | `/api/v1/pokedex/{entry_id}` | Actualizar apodo, captura, fecha, notas o favorito |
| DELETE | `/api/v1/pokedex/{entry_id}` | Quitar una entrada |
| POST / GET | `/api/v1/teams` | Crear y listar equipos de batalla |
| GET / PUT / DELETE | `/api/v1/teams/{team_id}` | Consultar, actualizar o borrar un equipo |
| GET | `/api/v1/teams/{team_id}/export` | Descargar un equipo en PDF |
| GET | `/api/v2/pokedex` | Consultar la colección incluyendo cadenas evolutivas |

## Flujo de trabajo

- `main` contiene la versión estable y entregable.
- `develop` integra las funcionalidades.
- Cada funcionalidad se trabaja en `features/<nombre>` y se integra mediante un pull request revisado.
- El trabajo se organiza en las issues de GitHub del repositorio.
- El despliegue público en Render es opcional y aún no está configurado.

## Decisiones de Diseño

### Rate limiting

El registro está limitado a 5 solicitudes por hora y el login a 10 por minuto por dirección IP. Al superar el límite, la API responde con HTTP 429 y registra el evento. Se aplican límites menores a la autenticación para reducir intentos automatizados. Como mejora futura se pueden establecer cuotas específicas para todos los endpoints.

### Versionado

Las rutas llevan un prefijo explícito: `/api/v1` o `/api/v2`. Se abre una versión nueva cuando un cambio incompatible afecta las respuestas o el comportamiento de clientes existentes. La v2 añade, en paralelo a v1, `GET /api/v2/pokedex` con los mismos filtros y la cadena evolutiva; los demás endpoints siguen disponibles bajo `/api/v1`. La v1 seguirá disponible durante la transición; antes de retirarla se anunciarán la fecha y el periodo de migración, junto con cabeceras `Deprecation` y `Sunset`.

### Otras decisiones

- Cada cuenta solo puede consultar o modificar su propia colección y sus equipos.
- Se usa SQLModel para validar datos y parametrizar consultas.
- Las respuestas de PokeAPI se reducen a los campos que consume la aplicación y se mantienen en caché en memoria.
- La integración continua usa datos de prueba y mocks; no necesita llamar a PokeAPI.

## Decisiones de Seguridad

- Las contraseñas se almacenan con hash bcrypt; se exige un mínimo de longitud, una mayúscula y un número.
- Los JWT se firman con una clave de entorno y caducan tras 24 horas por defecto.
- El login devuelve el mismo mensaje si falla el usuario o la contraseña.
- Las rutas privadas responden con 401 si el token falta, es inválido o ha caducado. Los recursos ajenos responden 404.
- CORS usa la lista configurada en `CORS_ORIGINS` y limita métodos y cabeceras permitidos.
- Las claves y la URL de base de datos se configuran en variables de entorno.

## Mejoras Futuras

- Añadir límites diferenciados para el resto de endpoints.
- Completar exportaciones adicionales y estadísticas avanzadas.
- Configurar migraciones de base de datos, recuperación de contraseña y despliegue.
- Mantener las dependencias y reglas de acceso actualizadas.

En producción se debe usar HTTPS para proteger las credenciales, los JWT y los datos durante el transporte.
