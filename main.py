# Importa las clases necesarias de FastAPI, Pydantic y otros módulos
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional
import uuid # Para generar IDs únicos
import random # Para generar códigos cortos aleatorios
import string # Para obtener caracteres para los códigos cortos

# 1. Define los Modelos de Datos usando Pydantic
# Pydantic nos ayuda a definir la estructura de los datos
# y realiza validaciones automáticas.

# Modelo para la entrada de la URL larga al crear una URL corta
class URLCreate(BaseModel):
    long_url: HttpUrl # HttpUrl asegura que la entrada sea una URL válida

# Modelo para la respuesta cuando se ha acortado una URL
class URLShortened(BaseModel):
    long_url: HttpUrl
    short_code: str
    short_url: str # La URL completa acortada (ej. http://localhost:8000/xyz)

# Modelo para la información completa de una URL (para mostrar en un listado, si se implementa)
class URLInfo(BaseModel):
    id: str
    long_url: HttpUrl
    short_code: str
    short_url: str
    clicks: int = 0 # Contador de clics

# 2. Inicializa la aplicación FastAPI
app = FastAPI(
    title="API de Acortador de URLs",
    description="Una API RESTful para acortar URLs y gestionar redirecciones.",
    version="1.0.0",
    docs_url="/docs",       # URL para la documentación de Swagger UI
    redoc_url="/redoc"      # URL para la documentación de ReDoc
)

# Configura CORS (Cross-Origin Resource Sharing)
# Esto es crucial para que tu frontend (que se ejecutará en un origen diferente, ej. GitHub Pages)
# pueda hacer solicitudes a este backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite solicitudes desde cualquier origen. En producción, especifica tus dominios.
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

# 3. Simulación de una base de datos en memoria
# En una aplicación real, esto se conectaría a una base de datos persistente
# (ej. PostgreSQL, MongoDB, SQLite).
# Usamos un diccionario donde la clave es el código corto y el valor es el objeto URLInfo.
fake_db: Dict[str, URLInfo] = {}

# Función para generar un código corto único
def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits # Letras (mayúsculas/minúsculas) y números
    while True:
        short_code = ''.join(random.choice(characters) for i in range(length))
        if short_code not in fake_db: # Asegura que el código sea único
            return short_code

# 4. Implementa los Endpoints

@app.post(
    "/shorten",
    response_model=URLShortened,
    status_code=status.HTTP_201_CREATED,
    summary="Acortar una URL",
    description="Recibe una URL larga y devuelve una URL acortada única."
)
async def shorten_url(url_create: URLCreate, request: Request):
    """
    Acorta una URL larga.

    - **url_create**: Objeto URLCreate que contiene la URL larga.
    - **request**: Objeto Request para obtener la URL base del servidor.
    - **Retorna**: La URL acortada y el código corto.
    - **Lanza**: HTTPException si la URL ya ha sido acortada (opcional, para evitar duplicados).
    """
    long_url_str = str(url_create.long_url)

    # Opcional: Buscar si la URL larga ya existe para devolver el código existente
    for short_code, url_info in fake_db.items():
        if url_info.long_url == url_create.long_url:
            base_url = str(request.base_url).rstrip('/')
            return URLShortened(
                long_url=url_create.long_url,
                short_code=short_code,
                short_url=f"{base_url}/{short_code}"
            )

    short_code = generate_short_code()
    base_url = str(request.base_url).rstrip('/') # Obtiene la URL base del servidor (ej. http://127.0.0.1:8000)
    short_url_full = f"{base_url}/{short_code}"

    # Almacena la información de la URL en la "base de datos"
    fake_db[short_code] = URLInfo(
        id=str(uuid.uuid4()),
        long_url=url_create.long_url,
        short_code=short_code,
        short_url=short_url_full,
        clicks=0
    )
    return URLShortened(long_url=url_create.long_url, short_code=short_code, short_url=short_url_full)

@app.get(
    "/{short_code}",
    summary="Redirigir a la URL larga",
    description="Redirige al usuario a la URL original asociada con el código corto."
)
async def redirect_to_long_url(short_code: str):
    """
    Redirige un código corto a su URL larga correspondiente.

    - **short_code**: El código corto generado.
    - **Retorna**: Una redirección HTTP 307 (Temporal Redirect) a la URL larga.
    - **Lanza**: HTTPException 404 si el código corto no se encuentra.
    """
    if short_code not in fake_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL corta no encontrada"
        )
    
    url_info = fake_db[short_code]
    url_info.clicks += 1 # Incrementa el contador de clics
    # En una DB real, aquí harías un update para persistir el contador
    return RedirectResponse(url=url_info.long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.get(
    "/urls/all",
    response_model=List[URLInfo],
    summary="Obtener todas las URLs acortadas",
    description="Recupera una lista de todas las URLs acortadas y sus estadísticas."
)
async def get_all_urls():
    """
    Recupera una lista de todas las URLs acortadas.
    (Solo para propósitos de demostración/administración)
    """
    return list(fake_db.values())

@app.get(
    "/urls/{short_code}/stats",
    response_model=URLInfo,
    summary="Obtener estadísticas de una URL acortada",
    description="Recupera la información y el número de clics de una URL acortada específica."
)
async def get_url_stats(short_code: str):
    """
    Obtiene las estadísticas de una URL acortada.

    - **short_code**: El código corto de la URL.
    - **Retorna**: Objeto URLInfo con los detalles y el contador de clics.
    - **Lanza**: HTTPException 404 si el código corto no se encuentra.
    """
    if short_code not in fake_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="URL corta no encontrada"
        )
    return fake_db[short_code]