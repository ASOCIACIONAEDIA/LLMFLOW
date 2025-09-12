import os
# Load environment variables FIRST
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Now import other modules that might need the loaded env vars
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query, Depends, status, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, AnyHttpUrl, ValidationError, field_validator, Field
from typing import Optional, Union, List, Dict, Literal, Any
from datetime import datetime, timedelta, timezone as dt_timezone
import requests
import asyncio
from contextlib import asynccontextmanager
from scrapers.main_trustpilot import reviews_trustpilot, gather_trustpilot_urls
from scrapers.main_tripadvisor import reviews_tripadvisor, gather_tripadvisor_urls
from scrapers.main_google import reviews_google, search_google_places_detailed
from scrapers.main_druni import reviews_druni
from scrapers.brightdata_amazon_handler import trigger_amazon_keyword_discovery, download_data_from_url, get_snapshot_results, trigger_manual_product_lookup, trigger_amazon_reviews_scrape, AMAZON_DOMAINS
from gold.clean_amazon import clean_amazon_reviews, separate_urls_and_asins
from helper.utilsdb import audit_request, grab_reviews_from_db, get_job_status_from_db, audit_id_from_db, update_audit, query_reviews_for_report_async, save_report_to_mongodb, fetch_generated_reports_for_brand, fetch_single_generated_report, delete_generated_report, save_discovered_product_in_db, delete_discovered_product_from_db, fetch_discovered_products, update_job_status_mysql
from models import SourceData
import logging
import aiohttp
import json
from fastapi.responses import JSONResponse, StreamingResponse
from helper.aws_informe_save import save_reviews_to_s3
from bson import ObjectId
import mysql.connector
from mysql.connector import Error
import boto3
import io
from pymongo import MongoClient
import pandas as pd
import time
import re
# Importar la función para generar informes
from helper.informes import generar_informe_por_tipo, render_html_report
# Importar sys para obtener el ejecutable de Python
import sys 
from scrapers.amazon.scrape_multiple import main as scrape_multiple
import httpx # Or use requests/aiohttp for the external API call
import motor.motor_asyncio
from pymongo.errors import ServerSelectionTimeoutError # Add this import
from collections import defaultdict
import uuid
import time # Add time import for heartbeat timing
import redis.asyncio as aioredis # Added Redis import
import arq # Added ARQ import
from redis.asyncio import Redis as AIORedis

# Import the sse_utils initializer
from helper.sse_utils import ( 
    sse_dispatch_event,
    # _sse_client_queues,
    # _sse_event_subscriptions,
    # _sse_subscription_lock
)


# Importar funciones de autenticación y usuarios
from auth import (
    UserLogin, AdminLogin, UserRegister, AdminRegister, MarcaCreate, TwoFactorVerifyRequest,
    get_current_user, get_current_admin, authenticate_user, authenticate_admin,
    authenticate_corporate_admin,
    register_user, register_admin, create_access_token,
    get_marcas_by_admin, get_marca_by_id, create_marca, update_marca, delete_marca,
    get_usuarios_by_admin, create_usuario, update_usuario, toggle_usuario_status,
    get_marca_name_by_id,
    get_current_admin_or_corporate,
    generate_2fa_code, store_2fa_code, send_2fa_email, verify_and_consume_2fa_code,
    get_db_connection, ACCESS_TOKEN_EXPIRE_MINUTES
)
# Importar funciones auxiliares para informes
from helper.aws_save import save_report_to_s3
# Importar la nueva función de generación de arquetipos
from helper.arquetype import run_archetype_generation, fetch_archetypes_from_db, fetch_single_archetype_details, run_archetype_generation_background, get_llm_chat_response
from fastapi import BackgroundTasks # Ensure BackgroundTasks is imported

# --- Logging Setup ---
# Get the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) # Set root logger level to INFO

# Configure the uvicorn.error logger (often used by FastAPI/Uvicorn for server errors)
uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.setLevel(logging.INFO) # Or WARNING if you want less from uvicorn itself

# Configure the uvicorn.access logger (for access logs)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO) # Or WARNING to reduce noise
# Add a handler for access logs if you want them formatted differently or sent elsewhere
# For now, we assume it will use the root logger's handlers if not configured.

# Specifically set the level for your scrapers module
scrapers_logger = logging.getLogger("scrapers") # Get the parent logger for all scrapers
scrapers_logger.setLevel(logging.INFO)

# Add a console handler to the root logger if no handlers are configured
# This ensures all INFO messages (from root, uvicorn, scrapers) go to console
if not root_logger.hasHandlers():
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s'
    )
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

# Your existing logger variable, can now point to a general app logger if preferred
# or you can continue to use specific loggers in different modules.
# For consistency with the rest of your app, you might get it from root or a specific app name.
logger = logging.getLogger(__name__) # This will be 'main' logger, will inherit from root.
# logger.setLevel(logging.INFO) # Not strictly necessary if root is INFO

# --- Use Uvicorn's Error Logger ---
# This logger is typically configured by Uvicorn to output to the console.
logger.setLevel(logging.INFO)
# ++ ADDED INITIALIZATION ++
# Dictionary to store event queues for report generation SSE
# report_generation_events: Dict[str, asyncio.Queue] = {} # -- REMOVED --
# scraping_job_events: Dict[str, asyncio.Queue] = {} # -- REMOVED --

# -- REMOVED: Global structures for multiplexed SSE --
# _sse_client_queues: Dict[str, asyncio.Queue] = {}
# _sse_event_subscriptions: Dict[str, set[str]] = defaultdict(set)
# _sse_subscription_lock = asyncio.Lock()

# Initialize FastAPI app

# Global Redis connection pool
_redis_pool: Optional[AIORedis] = None
_arq_redis_pool: Optional[arq.ArqRedis] = None # ARQ's special pool for enqueueing

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _redis_pool, _arq_redis_pool
    
    # Initialize MongoDB connection
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.critical("MONGODB_URI environment variable not set. MongoDB connection cannot be established.")
        app.state.mongo_client = None
    else:
        logger.info("Attempting to connect to MongoDB...")
        try:
            # Use AsyncIOMotorClient from motor
            app.state.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000 # Timeout after 5 seconds
            )
            # Ping the server to confirm the connection is actually alive.
            await app.state.mongo_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB.")
        except Exception as e:
            logger.error(f"FATAL: Failed to connect to MongoDB during startup: {e}", exc_info=True)
            app.state.mongo_client = None

    # Initialize Redis connection pool
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        # Standard redis-py pool for direct commands and SSE publishing
        _redis_pool = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await _redis_pool.ping() # Verify connection
        logger.info(f"Successfully connected standard Redis pool at {redis_url}")
        
        # ARQ pool for enqueueing jobs
        _arq_redis_pool = await arq.create_pool(
            arq.connections.RedisSettings.from_dsn(redis_url)
        )
        logger.info("Successfully connected ARQ Redis pool.")

    except aioredis.RedisError as e:
        logger.error(f"Error connecting to Redis during lifespan startup: {e}", exc_info=True)
        _redis_pool = None 
        _arq_redis_pool = None
        logger.warning("Redis-dependent systems (SSE, Task Queue) will not function.")
    except Exception as e:
        logger.error(f"Unexpected error during Redis initialization in lifespan: {e}", exc_info=True)
        _redis_pool = None
        _arq_redis_pool = None
        logger.warning("Redis-dependent systems (SSE, Task Queue) will not function.")
    
    yield
    
    # Shutdown
    if hasattr(app.state, "mongo_client") and app.state.mongo_client:
        logger.info("Closing MongoDB connection...")
        app.state.mongo_client.close()
        logger.info("MongoDB connection closed.")
        
    if _redis_pool:
        try:
            await _redis_pool.aclose()
            logger.info("Standard Redis connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing standard Redis connection pool: {e}", exc_info=True)
    if _arq_redis_pool:
        try:
            await _arq_redis_pool.aclose()
            logger.info("ARQ Redis connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing ARQ Redis connection pool: {e}", exc_info=True)
 
# Service configuration
SERVICE_BASE_URL = os.getenv("APP_BASE_URL")
PORT = int(os.getenv("PORT", "8000"))
DEFAULT_MAX_REVIEWS = int(os.getenv("DEFAULT_MAX_REVIEWS", "5"))

# Webhook configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BRIGHTDATA_WEBHOOK_SECRET = os.getenv("BRIGHTDATA_WEBHOOK_SECRET")

# Configuración S3 para reportes
AWS_S3_REPORTS_BUCKET = os.getenv("AWS_S3_BUCKET_REPORTS")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1") # O la región por defecto que uses

# Keep the handler setup as a fallback or for more control if propagate doesn't work alone
if not logger.handlers: 
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

app = FastAPI(lifespan=lifespan)
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure this class definition is ABOVE the endpoint function
class GooglePlaceSearchRequest(BaseModel):
    brand_name_or_query: str
    countries: Optional[List[str]] = Field(default_factory=list)
    selected_provinces: Optional[List[str]] = Field(default_factory=list)

# Modelo Pydantic para la solicitud de generación de informe
class ReportRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sources: List[str]
    countries: Optional[List[str]] = Field(default_factory=list)
    report_type: str
    archetype_id: Optional[str] = None
    products: Optional[List[str]] = None

# Modelo Pydantic para la solicitud de guardado de informe
class SaveReportRequest(BaseModel):
    html_content: str
    brand_name: str # Necesitamos pasar el nombre de la marca
    report_type: str

class ReviewCountRequest(BaseModel):
    start_date: Optional[str] = None # Expect ISO string format
    end_date: Optional[str] = None   # Expect ISO string format
    sources: List[str]
    countries: Optional[List[str]] = []

class ReverseGeocodeRequest(BaseModel):
    latitude: float
    longitude: float

class CompetitorSourceConfig(BaseModel):
    source_type: str
    brand_name: Optional[str] = None
    countries: Optional[List[str]] = Field(default_factory=list)
    number_of_reviews: Optional[int] = 1000
    is_brand_query: Optional[bool] = False
    google_config: Optional[Dict[str, Any]] = None

class Competitor(BaseModel):
    id: str = Field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:12]}")
    name: str
    sources: List[CompetitorSourceConfig] = Field(default_factory=list)

class CompetitorCreate(BaseModel):
    name: str

class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
# Dependency to get the database client
async def get_db(request: Request) -> motor.motor_asyncio.AsyncIOMotorDatabase:
    if not hasattr(request.app.state, "mongo_client") or not request.app.state.mongo_client:
        logger.error("MongoDB client not available. It might have failed to connect on startup. Check lifespan startup logs.")
        raise HTTPException(
            status_code=503, detail="Database connection is not available."
        )
    db_client = request.app.state.mongo_client
    db_name = os.getenv("MONGO_DB_NAME")
    if not db_name:
        logger.error("MONGO_DB_NAME environment variable is not set.")
        raise HTTPException(
            status_code=500, detail="Database configuration error."
        )
    return db_client[db_name]
# Función auxiliar para enviar webhooks
async def send_completion_webhook(job_id: str, s3_paths: Dict[str, str]):
    """Send a webhook notification with S3 paths when all scrapers are done"""
    if not WEBHOOK_URL:
        logger.warning("No webhook URL configured. Skipping webhook notification.")
        return

    try:
        payload = {
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "s3_paths": s3_paths,
            "status": "completed"
        }
        
        headers = {}
        if WEBHOOK_SECRET:
            headers["X-Webhook-Secret"] = WEBHOOK_SECRET

        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Webhook notification failed with status {response.status}")
                else:
                    logger.info(f"Successfully sent webhook notification for job {job_id}")
    except Exception as e:
        logger.error(f"Error sending webhook notification: {str(e)}")

# Función para guardar/actualizar configuraciones de sources ACTIVAS en MySQL
def save_source_config(usuario_id: int, source_data: SourceData):
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        sql = """
        INSERT INTO source_config (usuario_id, source_type, brand_name, countries, number_of_reviews, is_active)
        VALUES (%s, %s, %s, %s, %s, TRUE) # Siempre TRUE
        ON DUPLICATE KEY UPDATE
            brand_name = VALUES(brand_name),
            countries = VALUES(countries),
            number_of_reviews = VALUES(number_of_reviews),
            is_active = TRUE,
            updated_at = CURRENT_TIMESTAMP
        """
        cursor.execute(
            sql,
            (
                usuario_id,
                source_data.source_type,
                source_data.brand_name,
                json.dumps(source_data.countries),
                source_data.number_of_reviews
            )
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        logger.error(f"Error saving/updating active source config to MySQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar o actualizar la configuración activa: {str(e)}"
        )

# Función para obtener configuraciones de sources de un usuario
def get_user_source_configs(usuario_id: int):
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM source_config WHERE usuario_id = %s AND is_active = TRUE",
            (usuario_id,)
        )
        configs = cursor.fetchall()
        result = []
        for config in configs:
            if isinstance(config["countries"], str):
                config["countries"] = json.loads(config["countries"])
            result.append(config)
        cursor.close()
        conn.close()
        return result
    except Error as e:
        logger.error(f"Error getting source configs from MySQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener configuraciones: {str(e)}"
        )

# Función para guardar trabajo de scraping en MySQL
def save_job(job_id: str, usuario_id: int):
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (id, usuario_id, status) VALUES (%s, %s, %s)",
            (job_id, usuario_id, "pending")
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        logger.error(f"Error saving job to MySQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el trabajo: {str(e)}"
        )

# Función para actualizar estado y paths de trabajo (no se usará en la verificación)
def update_job_s3_paths(job_id: str, s3_paths: Dict[str, str]):
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET s3_paths = %s, status = %s WHERE id = %s",
            (json.dumps(s3_paths), "completed", job_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        logger.error(f"Error updating job in MySQL: {e}")

# Rutas de autenticación
@app.post("/api/auth/login")
async def login(user_data: UserLogin, background_tasks: BackgroundTasks):
    logger.info(f"Login request received for user: {user_data.email}")
    authenticated, user = await authenticate_user(user_data.email, user_data.password)
    logger.info(f"Login result: authenticated={authenticated}, user={user}")
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # --- Inicio Lógica 2FA ---
    user_id = user['id']
    user_email = user['email']
    
    # Generar y almacenar código 2FA
    code = generate_2fa_code()
    try:
        store_2fa_code(user_id, code)
    except Exception as e:
        # Si falla el almacenamiento del código, no podemos proceder con 2FA
        print(f"Error crítico al almacenar código 2FA para {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al preparar la autenticación de dos factores."
        )
    
    # Enviar correo en segundo plano
    background_tasks.add_task(send_2fa_email, user_email, code)
    
    # Devolver respuesta indicando que se requiere 2FA
    return {"status": "2fa_required", "user_id": user_id}
    # --- Fin Lógica 2FA ---

@app.post("/api/auth/verify-2fa")
async def verify_two_factor(request_data: TwoFactorVerifyRequest):
    # Verificar el código
    is_valid = verify_and_consume_2fa_code(request_data.user_id, request_data.code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Código 2FA inválido o expirado."
        )
    
    # Si el código es válido, obtener datos del usuario (necesario para el token)
    # (Podríamos optimizar esto si la info básica ya estuviera en la sesión/caché,
    # pero volver a buscar es más seguro y simple por ahora)
    conn = get_db_connection() # Necesitamos importar get_db_connection si no está ya
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT u.*, m.name as marca_name FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.id = %s",
            (request_data.user_id,)
        )
        user = cursor.fetchone()
        if not user:
             # Esto no debería pasar si store_2fa_code funcionó, pero por seguridad
             raise HTTPException(status_code=404, detail="Usuario no encontrado después de verificar 2FA.")
        user.pop("password", None) # Quitar password antes de crear token
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
    # Crear el token JWT final
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) # Asegúrate que ACCESS_TOKEN_EXPIRE_MINUTES esté definido
    access_token = create_access_token(
        data={"sub": str(user['id']), "role": "user"}, # Asignar rol "user"
        expires_delta=access_token_expires
    )
    
    # Devolver el token y los datos del usuario (como hacía el login original)
    return {
        "token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/api/auth/admin/login")
async def admin_login(admin_data: AdminLogin):
    authenticated, admin = await authenticate_admin(admin_data.email, admin_data.password)
    
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(admin["id"]), "role": "admin"}
    )
    
    return {"token": access_token, "token_type": "bearer", "admin": admin}

@app.post("/api/auth/corporate/login")
async def corporate_admin_login(admin_data: AdminLogin):
    """Endpoint para el login de administradores corporativos (tabla 'corporate_admins')."""
    authenticated, admin = await authenticate_corporate_admin(admin_data.email, admin_data.password)
    
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales corporativas incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token con rol específico "corporate_admin"
    access_token = create_access_token(
        data={"sub": str(admin["id"]), "role": "corporate_admin"} 
    )
    
    return {"token": access_token, "token_type": "bearer", "admin": admin}

@app.post("/api/auth/register")
async def user_register(user_data: UserRegister):
    user = register_user(user_data)
    return {"message": "Usuario registrado exitosamente", "user": user}

@app.post("/api/auth/admin/register")
async def admin_register(admin_data: AdminRegister):
    admin = register_admin(admin_data)
    return {"message": "Administrador registrado exitosamente", "admin": admin}

# Rutas para administración de marcas
@app.get("/api/admin/marcas")
async def get_marcas(admin_data = Depends(get_current_admin_or_corporate)):
    marcas = get_marcas_by_admin(admin_data)
    return marcas

@app.get("/api/admin/marcas/{marca_id}")
async def get_marca(marca_id: int, admin_data = Depends(get_current_admin_or_corporate)):
    logger.info(f"Getting marca with id: {marca_id} for admin data: {admin_data}")
    marca = get_marca_by_id(marca_id, admin_data)
    logger.info(f"Marca: {marca}")
    return marca

@app.post("/api/admin/marcas")
async def create_new_marca(marca_data: MarcaCreate, admin_data = Depends(get_current_admin_or_corporate)):
    logger.info(f"Executing create_new_marca for {marca_data} by {admin_data}") # Added a log here
    marca = create_marca(marca_data, admin_data)
    return marca

@app.put("/api/admin/marcas/{marca_id}")
async def update_existing_marca(marca_id: int, marca_data: MarcaCreate, admin_data = Depends(get_current_admin_or_corporate)):
    marca = update_marca(marca_id, marca_data, admin_data)
    return marca

@app.delete("/api/admin/marcas/{marca_id}")
async def delete_existing_marca(marca_id: int, admin_data = Depends(get_current_admin_or_corporate)):
    success = delete_marca(marca_id, admin_data)
    return {"success": success}

# Rutas para administración de usuarios
@app.get("/api/admin/usuarios")
async def get_usuarios(admin_data = Depends(get_current_admin_or_corporate)):
    logger.info(f"Getting usuarios for admin data: {admin_data}")
    usuarios = get_usuarios_by_admin(admin_data)
    logger.info(f"Usuarios: {usuarios}")
    return usuarios

@app.post("/api/admin/usuarios")
async def create_new_usuario(usuario_data: UserRegister, admin_data = Depends(get_current_admin_or_corporate)):
    usuario = create_usuario(usuario_data, admin_data)
    return usuario

@app.put("/api/admin/usuarios/{usuario_id}")
async def update_existing_usuario(usuario_id: int, usuario_data: dict, admin_data = Depends(get_current_admin_or_corporate)):
    usuario = update_usuario(usuario_id, usuario_data, admin_data)
    return usuario

@app.patch("/api/admin/usuarios/{usuario_id}/toggle-status")
async def toggle_existing_usuario_status(usuario_id: int, admin_data = Depends(get_current_admin_or_corporate)):
    usuario = toggle_usuario_status(usuario_id, admin_data)
    return usuario

# Rutas para sources de reviews
@app.get("/api/sources/config")
async def get_sources_config(user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    configs = get_user_source_configs(usuario_id)
    return configs

# First, we send the request for the google revies places, in order to see it in the UI
@app.post("/api/reviews/google/places")
async def google_places_search(request: GooglePlaceSearchRequest, user_data = Depends(get_current_user)):
    global _arq_redis_pool
    if not _arq_redis_pool:
        logger.error("Cannot enqueue google places search. ARQ Redis pool is not available.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue service is currently unavailable."
        )

    task_id = str(uuid.uuid4())
    usuario_id = int(user_data["sub"])
    logger.info(f"[{task_id}] User {usuario_id} initiated Google Places search for: '{request.brand_name_or_query}'")

    try:
        await _arq_redis_pool.enqueue_job(
            'search_google_places_task',
            task_id,
            request.brand_name_or_query,
            request.countries,
            request.selected_provinces
        )
        logger.info(f"[{task_id}] Enqueued 'search_google_places_task'.")
        return {"message": "Google Places search initiated.", "discovery_task_id": task_id}
    except Exception as e:
        logger.error(f"[{task_id}] Error enqueuing 'search_google_places_task': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue search task.")

async def check_and_finalize_job(redis_pool: aioredis.Redis, job_id: str, source_type: str, source_result: Any):
    """
    Checks job completion status using Redis.
    Increments completed source count, stores results, and dispatches SSE events.
    Finalizes the job if all sources have reported back.
    """
    if not redis_pool:
        logger.error(f"[{job_id}] Cannot check job completion. Redis pool is not available.")
        return

    try:
        # Retrieve job metadata from Redis
        job_data = await redis_pool.hgetall(f"job:{job_id}")
        if not job_data:
            logger.warning(f"[{job_id}] No job data found in Redis for completion check. Source '{source_type}' finished but cannot track overall progress.")
            return
            
        total_sources_for_job = int(job_data.get("total_sources", 0))

        # Use a transaction (pipeline) for atomic operations
        async with redis_pool.pipeline() as pipe:
            pipe.hincrby(f"job:{job_id}", "completed_count", 1)
            # Store the result for this source, converting it to a JSON string
            pipe.hset(f"job:{job_id}:results", source_type, json.dumps(source_result))
            await pipe.execute()
        
        completed_count = int(await redis_pool.hget(f"job:{job_id}", "completed_count"))

        logger.info(f"[{job_id}] Source '{source_type}' completed. Total completed: {completed_count}/{total_sources_for_job}.")

        await sse_dispatch_event(redis_pool, job_id, "scrape_tracking", {
            "status": "source_complete",
            "source_type": source_type,
            "message": f"Source '{source_type}' completed processing.",
            "processed_sources": completed_count,
            "total_sources_to_track": total_sources_for_job
        })

        if total_sources_for_job > 0 and completed_count >= total_sources_for_job:
            logger.info(f"[{job_id}] All {total_sources_for_job} sources have completed. Finalizing job.")
            
            all_results_raw = await redis_pool.hgetall(f"job:{job_id}:results")
            
            all_results = {}
            for k, v in all_results_raw.items():
                key = k.decode('utf-8') if isinstance(k, bytes) else k
                value_bytes = v.decode('utf-8') if isinstance(v, bytes) else v
                all_results[key] = json.loads(value_bytes)

            update_job_s3_paths(job_id, all_results)
            logger.info(f"[{job_id}] Updated job status and results in MySQL.")

            completed_data = {
                "status": "completed",
                "message": f"All sources for job [{job_id}] have completed.",
                "s3_paths": all_results,
                "processed_sources": completed_count,
                "total_sources_to_track": total_sources_for_job
            }
            await sse_dispatch_event(redis_pool, job_id, "scrape_tracking", completed_data)

            await redis_pool.delete(f"job:{job_id}", f"job:{job_id}:results")
            logger.info(f"[{job_id}] Cleaned up Redis keys for completed job.")
            
    except Exception as e:
        logger.error(f"[{job_id}] Error in check_and_finalize_job for source '{source_type}': {e}", exc_info=True)

SCRAPER_TASK_MAP = {
    "trustpilot": "scrape_trustpilot_task",
    "tripadvisor": "scrape_tripadvisor_task",
    "google": "scrape_google_task",
    "mybusiness": "scrape_google_task", # Add mapping for 'mybusiness'
}

async def _run_scraping_orchestration(
    job_id: str,
    active_sources_data: List[SourceData],
    usuario_id: str,
    brand_name: str,
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
):
    """
    Orchestrates the scraping process by enqueuing ARQ tasks for each active source.
    """
    logger.info(f"[{job_id}] Starting scraping orchestration for user {usuario_id} and brand '{brand_name}'.")
    
    # Store job metadata in Redis
    total_sources_to_track = 0
    source_types_to_enqueue = set()

    for source in active_sources_data:
        if source.source_type == "products":
            # For products, we might have multiple sub-sources (amazon, druni)
            # We will treat each one as a source to track if it has identifiers.
            product_source_data = source.model_dump()
            identifiers_str = product_source_data.get("brand_name", "")
            if not identifiers_str: continue # Skip if no products to scrape

            # Check which sub-sources are targeted
            # The frontend determines which identifiers go to which sub-source.
            # Here we assume the identifiers are for the given targets.
            # Based on ConnectSources.vue, identifiers are now filtered client-side before being sent.
            
            # For now, let's assume 'druni' might be a target inside products.
            # A better approach would be to have the frontend specify this.
            # Let's check for a flag or convention.
            # A simpler model for now: if source_type is 'druni', we run druni.
            # The user has configured the front-end to have druni as a scrapeTarget.
            # Let's assume for now that 'druni' comes as its own source_type if selected.
            # Looking at the frontend, 'products' is the source, and it has scrapeTargets.
            # The backend receives a list of sources.
            # The frontend seems to send 'druni' as a scrapeTarget for a product, not a top-level source.
            # The current logic joins all product URLs into one string.
            
            # The most straightforward change is to handle 'druni' as a top-level source type.
            # Let's check the frontend logic `saveAndGather`
            # The logic sends `source_type: sourceElement.id`. The `id` for products is just 'products'.
            # The logic to split by target (amazon, druni) must happen here.

            # Let's assume a simplified flow for now where if druni is enabled, we get a 'druni' source type.
            # If the source is 'products', we will check for druni targets. This is getting complex.
            
            # The user said "if the user chooses druni as a source". This implies it's a selectable source.
            # The vue file shows `druni` as a `scrapeTarget`.
            # A simple implementation is to just look for a source with id 'druni'.
            pass # We will handle product logic below based on source_type.

        else:
            source_types_to_enqueue.add(source.source_type)

    total_sources_to_track = len(active_sources_data)

    await _redis_pool.hset(f"job:{job_id}", mapping={
        "user_id": usuario_id,
        "brand_name": brand_name,
        "status": "enqueued",
        "total_sources": total_sources_to_track,
        "completed_count": 0
    })

    # Enqueue tasks for each source
    for source_data in active_sources_data:
        source_type = source_data.source_type
        task_name = f"scrape_{source_type}_task"
        
        # This structure assumes a direct mapping from source_type to task name.
        # e.g., source_type 'google' -> 'scrape_google_task'
        # e.g., source_type 'druni' -> 'scrape_druni_task'
        
        try:
            logger.info(f"[{job_id}] Enqueuing task '{task_name}' for source '{source_type}'.")
            await _arq_redis_pool.enqueue_job(
                task_name,
                job_id,
                source_data.model_dump(),
                usuario_id,
                brand_name
            )
        except Exception as e:
            logger.error(f"[{job_id}] Failed to enqueue task '{task_name}': {e}", exc_info=True)
            # Decrement total sources if a task fails to enqueue
            await _redis_pool.hincrby(f"job:{job_id}", "total_sources", -1)

@app.post("/api/reviews/")
async def orchestrator_scrape(active_sources_data: List[SourceData], background_tasks: BackgroundTasks, user_data = Depends(get_current_user), db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)):
    """
    Main endpoint to trigger the scraping and data processing orchestration.
    It receives the source configurations from the frontend, creates a job ID,
    and starts the background process.
    """
    usuario_id = int(user_data['sub'])
    marca_id = user_data.get('marca_id')
    job_id = str(uuid.uuid4())
    save_job(job_id, usuario_id)

    brand_name = "UnknownBrand" # Default brand name
    if usuario_id:
        try:
            # Fetch the brand name using the provided utility function
            fetched_brand_name = get_marca_name_by_id(usuario_id)
            if fetched_brand_name:
                brand_name = fetched_brand_name
            else:
                logger.warning(f"No brand name found for marca_id {marca_id}. Defaulting to 'UnknownBrand'.")
        except Exception as e:
            logger.error(f"Could not retrieve brand name for marca_id {marca_id}: {e}")
            brand_name = "UnknownBrand"

    logger.info(f"[{job_id}] Starting scraping orchestration for {len(active_sources_data)} sources. Main brand: '{brand_name}'")
    
    background_tasks.add_task(
        _run_scraping_orchestration,
        job_id,
        active_sources_data,
        usuario_id,
        brand_name,
        db
    )

    return {"message": "Scraping process initiated.", "job_id": job_id}

@app.get("/api/reviews/scrape_status/{job_id}")
async def review_scrape_status_sse(job_id: str, request: Request):
    # This endpoint is now superseded by the unified /api/sse/stream
    # It can be removed or marked as deprecated.
    # For now, let's raise a 404 or redirect if a client tries to use it.
    logger.warning(f"Deprecated endpoint /api/reviews/scrape_status/{job_id} called. Use /api/sse/stream instead.")
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="This SSE endpoint is deprecated. Please use /api/sse/stream.")

@app.get("/api/job_status/{id}")
async def get_job_status(id: str, user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM jobs WHERE id = %s AND usuario_id = %s",
            (id, usuario_id)
        )
        job = cursor.fetchone()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trabajo no encontrado o no tiene permisos para acceder a él"
            )
        
        cursor.close()
        conn.close()
        
        return {"status": job["status"], "s3_paths": json.loads(job["s3_paths"]) if job["s3_paths"] else {}}
    except Error as e:
        logger.error(f"Error getting job status from MySQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estado del trabajo: {str(e)}"
        )

@app.get("/api/health")
async def health():
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return {"status": "ok", "database": "connected"}
        return {"status": "error", "database": "disconnected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/health_check")
async def health_check():
    return await health()

@app.post("/api/webhook/final_report/{id}")
async def webhook_final_report(request: Request, id: str):
    """Webhook para generar el informe final cuando todos los scrapers han terminado"""
    logger.info(f"Recibida solicitud para generar informe final para job {id}")
    try:
        mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "insights_db")
        }
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM jobs WHERE id = %s", (id,))
        job = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not job:
            logger.error(f"Informe final: Job {id} no encontrado.")
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        
        if not job["s3_paths"]:
            logger.error(f"Informe final: No hay rutas S3 (limpias) para job {id}.")
            return JSONResponse(status_code=400, content={"error": "No S3 paths found for this job"})
        
        try:
            s3_cleaned_paths = json.loads(job["s3_paths"])
        except json.JSONDecodeError:
            logger.error(f"Informe final: Error decodificando s3_paths JSON para job {id}.")
            return JSONResponse(status_code=500, content={"error": "Error decoding S3 paths"})

        if not s3_cleaned_paths:
            logger.warning(f"Informe final: s3_paths está vacío para job {id}. No se generarán informes.")
            return JSONResponse(status_code=200, content={"message": "No cleaned data paths found, no reports generated."}) 

        first_path = next(iter(s3_cleaned_paths.values()), None)
        if not first_path:
            logger.error(f"Informe final: No se pudo obtener una ruta S3 válida de {s3_cleaned_paths} para job {id}.")
            return JSONResponse(status_code=500, content={"error": "Invalid S3 path structure"})
        
        try:
            path_parts = first_path.split('/')
            if len(path_parts) > 1:
                company_name = path_parts[0]
            else:
                logger.error(f"Informe final: No se pudo extraer company_name de la ruta {first_path}")
                company_name = "unknown_company" 
        except Exception as path_e:
            logger.error(f"Informe final: Error parseando company_name de {first_path}: {path_e}")
            company_name = "unknown_company"

        logger.info(f"Informe final: Iniciando generación para job {id}, company: {company_name}")
        generated_report_paths = {}
        pdf_paths = {}
        
        AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
        AWS_S3_BUCKET_HTML = os.getenv("AWS_S3_BUCKET_HTML")
        s3_client = boto3.client('s3', ...)
        
        try:
            import weasyprint
        except ImportError:
            logger.error("La librería 'weasyprint' no está instalada. No se podrán generar PDFs.")
            weasyprint = None

        for platform, s3_cleaned_path in s3_cleaned_paths.items():
            try:
                logger.info(f"Informe final [{id}]: Procesando {platform} desde {s3_cleaned_path}")
                obj = s3_client.get_object(Bucket=AWS_S3_BUCKET, Key=s3_cleaned_path)
                cleaned_content = obj['Body'].read().decode('utf-8')
                cleaned_data = json.loads(cleaned_content)
                if not cleaned_data:
                    logger.warning(f"Informe final [{id}]: Datos limpios vacíos para {platform}. Saltando informe.")
                    continue

                cleaned_df = pd.DataFrame(cleaned_data)
                report_type = "analisis_sentimientos"
                html_report_content = generar_informe_por_tipo(cleaned_df, report_type)
                
                if not html_report_content:
                    logger.error(f"Informe final [{id}]: Falló la generación de informe HTML para {platform}.")
                    continue

                now = datetime.now(datetime.timezone.utc)
                timestamp_html = now.strftime("%Y-%m-%d_%H-%M-%S")
                html_file_name = f"{platform}_informe_{report_type}_{timestamp_html}.html"
                partition_date = now.strftime("%Y-%m-%d")
                html_s3_path = f"{company_name}/{platform}/REPORTS/PARTITION_DATE={partition_date}/{html_file_name}"
                
                html_buffer = io.BytesIO(html_report_content.encode('utf-8'))
                html_buffer.seek(0)
                s3_client.upload_fileobj(html_buffer, AWS_S3_BUCKET_HTML, html_s3_path)
                generated_report_paths[platform] = f"s3://{AWS_S3_BUCKET_HTML}/{html_s3_path}"
                logger.info(f"Informe final [{id}]: Informe HTML para {platform} guardado en {generated_report_paths[platform]}")

                if weasyprint:
                    try:
                        pdf_content = weasyprint.HTML(string=html_report_content).write_pdf()
                        pdf_buffer = io.BytesIO(pdf_content)
                        pdf_buffer.seek(0)
                        pdf_s3_path = html_s3_path.replace(".html", ".pdf")
                        s3_client.upload_fileobj(pdf_buffer, AWS_S3_BUCKET_HTML, pdf_s3_path)
                        pdf_paths[platform] = f"s3://{AWS_S3_BUCKET_HTML}/{pdf_s3_path}"
                        logger.info(f"Informe final [{id}]: Informe PDF para {platform} guardado en {pdf_paths[platform]}")
                    except Exception as pdf_e:
                        logger.error(f"Informe final [{id}]: Error generando o guardando PDF para {platform}: {pdf_e}")
                
            except Exception as report_e:
                logger.error(f"Informe final [{id}]: Error procesando {platform}: {report_e}")
                import traceback
                traceback.print_exc()
                continue
        
        final_status = "reports_generated" if generated_report_paths else "reports_failed"
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET status = %s, report_paths = %s WHERE id = %s", 
            (final_status, json.dumps({"html": generated_report_paths, "pdf": pdf_paths}), id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Informe final [{id}]: Proceso completado. Estado: {final_status}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Report generation finished with status: {final_status}",
                "html_report_paths": generated_report_paths,
                "pdf_report_paths": pdf_paths
            }
        )

    except Exception as e:
        error_message = f"Error general en webhook_final_report para job {id}: {str(e)}"
        logger.error(error_message)
        import traceback
        traceback.print_exc()
        try:
            conn = mysql.connector.connect(**mysql_config)
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = %s WHERE id = %s", ("error_report_generation", id))
            conn.commit()
            cursor.close()
            conn.close()
        except:
            logger.error(f"Informe final [{id}]: Falló incluso la actualización de estado a error.")
            
        return JSONResponse(
            status_code=500,
            content={"error": error_message}
        )

# Endpoint para obtener países
@app.get("/api/countries/")
async def get_countries():
    try:
        with open("countries.json", "r", encoding="utf-8") as f:
            countries_data = json.load(f)
        return countries_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Countries file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error decoding countries JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/api/user/me")
async def get_user_info(user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    marca_name = get_marca_name_by_id(usuario_id)
    return {"id": usuario_id, "marca_name": marca_name}

# --- ENDPOINT PARA GENERAR INFORMES --- 
@app.post("/api/reports/generate")
async def generate_report_html_async(
    report_request: ReportRequest,
    background_tasks: BackgroundTasks,
    user_data: dict = Depends(get_current_user) # user_data is a dict
):
    # current_user is user_data, which is a dictionary (JWT payload)
    # The user ID is in the 'sub' field of the JWT payload.
    try:
        usuario_id_str = user_data.get("sub")
        if not usuario_id_str:
            logger.error(f"User ID ('sub') not found in JWT payload: {user_data}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token: User ID missing.")
        usuario_id = int(usuario_id_str)
    except ValueError:
        logger.error(f"User ID ('sub') in JWT payload is not a valid integer: {user_data.get('sub')}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token: User ID format error.")

    # Fetch brand_name using the usuario_id
    # Assuming get_marca_name_by_id is an async function or can be awaited if synchronous
    # Based on its definition in auth.py, it seems synchronous.
    # If it's synchronous and might block, consider running it in a thread.
    # For now, assuming it's acceptable to call directly or it's fast.
    
    # Let's check if get_marca_name_by_id is async. The grep result shows it's a sync def.
    # It should be called with asyncio.to_thread if it involves I/O.
    
    brand_name = await asyncio.to_thread(get_marca_name_by_id, usuario_id)

    if not brand_name:
        logger.error(f"Could not retrieve brand name for user ID: {usuario_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Brand not found for user {usuario_id}.")

    task_id = str(uuid.uuid4())

    logger.info(f"Async report generation request received for user {usuario_id} (Brand: {brand_name}), type: {report_request.report_type}")

    background_tasks.add_task(
        _run_report_generation_logic,
        task_id,
        report_request,
        usuario_id,
        brand_name
    )

    logger.info(f"Task [{task_id}] for report type '{report_request.report_type}' for user {usuario_id} (Brand: {brand_name}) has been scheduled.")
    return {"message": "Report generation started", "task_id": task_id}


# --- ENDPOINT PARA GUARDAR EL INFORME EN S3 --- 
@app.post("/api/reports/save")
async def save_report_s3(save_request: SaveReportRequest, user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    logger.info(f"Report save request received for user {usuario_id}, brand: {save_request.brand_name}, type: {save_request.report_type}")

    # Validar que el usuario pertenece a la marca? (Opcional, pero bueno para seguridad)
    current_user_brand = get_marca_name_by_id(usuario_id)
    if current_user_brand != save_request.brand_name:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not belong to the specified brand.")

    # 1. Intentar guardar en S3
    try:
        s3_key = save_report_to_s3(
            html_content=save_request.html_content,
            brand_name=save_request.brand_name,
            report_type=save_request.report_type,
            bucket_name=AWS_S3_REPORTS_BUCKET
        )
        if not s3_key:
            raise Exception("save_report_to_s3 returned None, indicating a failure.")
            
    except Exception as s3_error:
        logger.error(f"Error saving report to S3: {s3_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el informe en S3: {s3_error}"
        )

    logger.info(f"Report saved to S3 with key: {s3_key}")

    # 2. Construir y devolver URL del informe
    if not AWS_S3_REPORTS_BUCKET or not AWS_REGION:
         logger.error("AWS S3 config (bucket/region) missing for URL construction.")
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail="Configuración del servidor incompleta para generar la URL del informe guardado."
         )
         
    report_url = f"https://{AWS_S3_REPORTS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    logger.info(f"Final report URL: {report_url}")

    return {"message": "Informe guardado en S3 exitosamente.", "report_url": report_url}

# --- ENDPOINT PARA GENERAR ARQUETIPOS --- 
@app.post("/api/archetypes/generate")
async def generate_archetypes_endpoint(
    background_tasks: BackgroundTasks, 
    user_data = Depends(get_current_user)
):
    usuario_id = int(user_data["sub"]) # This is fast
    logger.info(f"Archetype generation request received for user {usuario_id}")

    # Run the potentially blocking DB call in a separate thread
    brand_name = await asyncio.to_thread(get_marca_name_by_id, usuario_id) 
    
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} to generate archetypes.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )
    
    task_id = str(uuid.uuid4()) # This is fast
    logger.info(f"User {usuario_id} (Brand: {brand_name}) - Scheduling archetype generation task_id: {task_id}")

    # Schedule the actual generation as a background task
    background_tasks.add_task(run_archetype_generation_background, task_id, brand_name, _redis_pool)

    # Return response to client immediately
    return {
        "message": "Archetype generation process has been initiated.",
        "task_id": task_id
    }

@app.post("/api/reviews/count")
async def get_dynamic_review_count(
    count_request: ReviewCountRequest,
    user_data = Depends(get_current_user) # Reuse your auth dependency
):
    """
    Calculates the total number of reviews matching the provided filters.
    """
    usuario_id = int(user_data["sub"])
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        raise HTTPException(status_code=404, detail="Brand not found for user.")

    client = None
    total_count = 0

    # --- 1. Validate and Parse Dates (only if provided) ---
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    if count_request.start_date and count_request.end_date:
        try:
            start_dt = datetime.fromisoformat(count_request.start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(count_request.end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format provided.")
    elif count_request.start_date or count_request.end_date:
        # If only one date is provided, it's a bad request
        raise HTTPException(status_code=400, detail="Both start_date and end_date must be provided if filtering by date.")

    # --- 2. Connect to MongoDB (Choose Async or Sync) ---
    # Example using ASYNC (motor) - Adapt if using synchronous pymongo
    try:
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        await client.admin.command('ismaster') # Check connection async
        db = client["Reviews"]
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB for count: {e}")
        raise HTTPException(status_code=503, detail="Database connection error.")

    # --- 3. Determine Collections to Query ---
    collection_map = { # Use the same map as your report generation
        "trustpilot": "reviews_trustpilot_gold",
        "tripadvisor": "reviews_tripadvisor_gold",
        "google": "reviews_google_gold",
        "druni": "reviews_druni_gold",
        "amazon": "reviews_amazon_gold" 
    }
    collections_to_query = [collection_map[s.lower()] for s in count_request.sources if s.lower() in collection_map]
    logger.info(f"Collections to query: {collections_to_query}")

    if not collections_to_query:
        logger.warning("No valid sources selected for review count.")
        if client: client.close()
        return {"total_count": 0} # No valid sources selected

    # --- 4. Build Base Query Filter ---
    query_filter = {
        "brand_name": brand_name 
    }
    if start_dt and end_dt: # Only add date filter if dates were valid and provided
        query_filter["date"] = {"$gte": start_dt, "$lte": end_dt}
    
    if count_request.countries: # This is fine, empty list means no country filter by default
        uppercase_countries = [c.upper() for c in count_request.countries]
        query_filter["country"] = {"$in": uppercase_countries}

    # --- 5. Query Each Collection for Count ---
    # Using asyncio.gather for concurrency if using motor
    count_tasks = []
    async def count_in_collection(coll_name):
        try:
            collection = db[coll_name]
            # Check if collection exists before counting
            # Note: list_collection_names is blocking in motor < 2.6, may need workaround or sync check
            # A simpler check might be to just proceed and handle potential errors
            count = await collection.count_documents(query_filter)
            logger.debug(f"Count for {coll_name} with filter {query_filter}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting documents in '{coll_name}': {e}")
            return 0 # Return 0 if counting fails for a collection

    for coll_name in collections_to_query:
         if coll_name in await db.list_collection_names(): # Check if collection exists (async check)
             count_tasks.append(count_in_collection(coll_name))
         else:
             logger.warning(f"Collection '{coll_name}' not found, skipping count.")


    if count_tasks:
        counts = await asyncio.gather(*count_tasks)
        total_count = sum(counts)
    else:
        total_count = 0


    # --- 6. Cleanup and Return ---
    if client:
        client.close()

    logger.info(f"Dynamic count for brand '{brand_name}' with filters: {total_count}")
    return {"total_count": total_count}
# --- ENDPOINT PARA OBTENER ARQUETIPOS GENERADOS --- 
@app.get("/api/archetypes")
async def get_generated_archetypes(user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    logger.info(f"Get archetypes request received for user {usuario_id}")

    # 1. Obtener nombre de la marca del usuario
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} to fetch archetypes.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )
    logger.info(f"Fetching generated archetypes for brand: {brand_name}")

    # 2. Llamar a la función que lee y parsea desde MongoDB
    try:
        archetypes_data = fetch_archetypes_from_db(brand_name)
        if not archetypes_data:
            # Si no se encontraron datos, devolver 404 o 200 con lista vacía?
            # Devolver 404 si *nunca* se generaron puede ser mejor
            # Opcional: podrías comprobar si la colección existe antes de devolver 404
            logger.warning(f"No archetypes found in DB for brand {brand_name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No generated archetypes found for brand '{brand_name}'. Please generate them first."
            )
        return archetypes_data # Devolver la lista de arquetipos parseados
    except HTTPException as http_exc:
        # Relanzar excepciones HTTP que puedan venir de fetch_archetypes_from_db (ej. 503 DB error)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error fetching archetypes for brand {brand_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred while fetching archetypes."
        )

# --- NEW ENDPOINT TO GET LIST OF GENERATED REPORTS ---
@app.get("/api/reports/generated", response_model=List[Dict]) # Define response model if possible
async def get_generated_reports_list(user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    logger.info(f"Fetching generated reports list for user {usuario_id}")

    # 1. Get user's brand name
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} to fetch generated reports.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )
    logger.info(f"Fetching generated reports for brand: {brand_name}")

    # 2. Call the function to read from MongoDB
    try:
        # fetch_generated_reports_for_brand should return an empty list if none are found
        reports = fetch_generated_reports_for_brand(brand_name)
        return reports
    except Exception as e:
        logger.error(f"Unexpected error fetching generated reports for brand {brand_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred while fetching generated reports."
        )

# --- NEW ENDPOINT TO GET DETAIL OF A GENERATED REPORT ---
@app.get("/api/reports/generated/{report_id}", response_model=Dict) # Define response model if possible
async def get_generated_report_detail(report_id: str, user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    logger.info(f"Fetching detail for report ID {report_id} for user {usuario_id}")

    # 1. Get user's brand name
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} to fetch report {report_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )
    logger.info(f"User {usuario_id} belongs to brand {brand_name}. Fetching report {report_id}.")

    # 2. Call the function to read the specific report from MongoDB
    try:
        report_details = fetch_single_generated_report(report_id, brand_name)

        if report_details is None:
            # This handles both "not found" and "brand mismatch" from the util function
            logger.warning(f"Report {report_id} not found or access denied for brand {brand_name}.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' not found or you don't have permission to access it."
            )

        # Ensure the returned dictionary is JSON serializable (basic checks done in util)
        return report_details

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions (like 404 from above)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error fetching report detail {report_id} for brand {brand_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred while fetching the report details."
        )

@app.delete("/api/reports/generated/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_generated_report(report_id: str, user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    logger.info(f"Request to delete report ID {report_id} for user {usuario_id}")

    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} attempting to delete report {report_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )
    logger.info(f"User {usuario_id} (Brand: {brand_name}) attempting to delete report {report_id}.")

    try:
        # The delete_generated_report function handles brand checking internally
        was_deleted = delete_generated_report(report_id, brand_name)

        if not was_deleted:
            # This could mean not found, or brand mismatch (logged in utilsdb)
            # For the client, 404 is a reasonable response for "can't delete what's not there or not yours"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' not found or you don't have permission to delete it."
            )
        
        # If successful, FastAPI will return 204 No Content due to status_code in decorator
        logger.info(f"Report {report_id} successfully deleted for brand {brand_name}.")
        return # FastAPI handles the 204 response

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions (like 404 from above)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error deleting report {report_id} for brand {brand_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred while deleting the report."
        )

@app.get("/api/sources/review-counts")
async def get_review_counts(
    start_date_str: Optional[str] = Query(None, alias="start_date"),
    end_date_str: Optional[str] = Query(None, alias="end_date"),
    countries: Optional[List[str]] = Query(None), # Add countries parameter
    user_data = Depends(get_current_user)
):
    usuario_id = int(user_data["sub"])
    logger.info(f"Fetching reviews counts for user {usuario_id}, start: {start_date_str}, end: {end_date_str}, countries: {countries}")

    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} to fetch reviews counts.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )

    effective_start_dt: Optional[datetime] = None
    effective_end_dt: Optional[datetime] = None
    try:
        if start_date_str:
            effective_start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date_str:
            effective_end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        logger.error(f"Invalid date format provided: start='{start_date_str}', end='{end_date_str}'")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format provided.")

    if effective_start_dt and effective_end_dt and effective_start_dt > effective_end_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be after end date.")

    try:
        mongodb_uri = os.getenv("MONGODB_URI")
        client = MongoClient(mongodb_uri)
        db = client["Reviews"]

        source_mappings = {
            "reviews_google_gold": {"id": "google", "name": "Google", "brand_field": "brand_name", "country_field": "country"},
            "reviews_amazon_gold": {"id": "amazon", "name": "Amazon", "brand_field": "brand_name", "country_field": "country"},
            "reviews_trustpilot_gold": {"id": "trustpilot", "name": "Trustpilot", "brand_field": "brand_name", "country_field": "country"},
            "reviews_tripadvisor_gold": {"id": "tripadvisor", "name": "TripAdvisor", "brand_field": "brand_name", "country_field": "country"},
            "reviews_druni_gold": {"id": "druni", "name": "Druni", "brand_field": "brand_name", "country_field": "country"}
        }

        results = []
        for coll_name, info in source_mappings.items():
            count = 0
            if coll_name in db.list_collection_names():
                collection = db[coll_name]
                brand_field = info["brand_field"]
                country_field = info.get("country_field", "country") # Default to "country"

                query_filter = {brand_field: {"$regex": f"^{re.escape(brand_name)}$", "$options": "i"}} if brand_name else {}

                date_conditions = {}
                if effective_start_dt:
                    date_conditions["$gte"] = effective_start_dt
                if effective_end_dt:
                    date_conditions["$lte"] = effective_end_dt
                if date_conditions:
                    query_filter["date"] = date_conditions
                
                # Add country filter
                if countries: # If countries list is provided and not empty
                    # Ensure country codes are uppercase for matching, assuming DB stores them uppercase
                    uppercase_countries = [c.upper() for c in countries]
                    query_filter[country_field] = {"$in": uppercase_countries}

                logger.debug(f"Querying {coll_name} for brand '{brand_name}' with filter: {query_filter}")
                count = collection.count_documents(query_filter)
            
            results.append({"id": info["id"], "name": info["name"], "count": count})

        logger.info(f"Review counts for brand {brand_name} (filtered by date and countries): {results}")
        return results
    except Exception as e:
        logger.error(f"Error getting source review counts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch review counts: {str(e)}")
    finally:
        if 'client' in locals() and client:
            client.close()

@app.post("/api/maps/reverse-geocode")
async def reverse_geocode_location(request_data: ReverseGeocodeRequest, user_data = Depends(get_current_user)):
    usuario_id = int(user_data["sub"])
    google_api_key = os.getenv("GOOGLE_MAPS_GEOCODING_API_KEY") # Use a specific key for Geocoding if different
    if not google_api_key:
        raise HTTPException(status_code=500, detail="Geocoding API key not configured on server.")

    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={request_data.latitude},{request_data.longitude}&key={google_api_key}"
    
    # For production, use an async HTTP client if this endpoint is heavily used.
    # For simplicity here, using synchronous httpx.
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(geocode_url)
            response.raise_for_status() # Raise an exception for bad status codes
            geocode_data = response.json()

        if geocode_data.get("status") == "OK" and geocode_data.get("results"):
            # Process results to find a suitable place. 
            # The first result is often the most specific.
            # You'll need to parse 'formatted_address', 'place_id', 'name' (from address_components or geometry)
            # This part requires careful parsing of Google Geocoding API response.
            
            first_result = geocode_data["results"][0]
            # Construct a simplified place object similar to what Outscraper returns
            # This is a simplified example; you'll need to adapt it based on Geocoding API structure
            # and what your frontend expects.
            place_details = {
                "google_id": first_result.get("place_id", f"rev_geo_{request_data.latitude}_{request_data.longitude}"),
                "name": first_result.get("formatted_address", "Unknown Location"), # Or derive from components
                "full_address": first_result.get("formatted_address", ""),
                "latitude": request_data.latitude, # Echo back or use geometry from response
                "longitude": request_data.longitude,
                "category": "Map Selection" # Or derive from types
                # Add other fields as needed, potentially making another Places API call if you only get place_id
            }
            return place_details
        else:
            logger.error(f"Reverse geocoding failed or no results: {geocode_data.get('status')} - {geocode_data.get('error_message')}")
            raise HTTPException(status_code=404, detail="Could not find place information for the clicked location.")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during reverse geocoding: {e.response.text}")
        raise HTTPException(status_code=502, detail="Error communicating with geocoding service.")
    except Exception as e:
        logger.error(f"Error in reverse_geocode_location: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error during reverse geocoding.")

# --- NUEVO: Modelos Pydantic para Analytics Overview ---
class KPIReportItem(BaseModel):
    value: str
    change: str # e.g., "+10.5%" or "-2.0%" or "N/A"
    trend: Literal['up', 'down', 'neutral']

class AnalyticsOverviewResponse(BaseModel):
    totalReviews: KPIReportItem
    newReviews7d: KPIReportItem
    averageSentiment: KPIReportItem # Change might be omitted or handled differently
    lastUpdated: KPIReportItem

# --- NUEVO: Modelos Pydantic para Review Volume Trend ---
class ReviewVolumeTrendDataset(BaseModel):
    label: str = "Total Reviews"
    data: List[int]
    borderColor: str = "#6366F1"
    backgroundColor: str = "rgba(99, 102, 241, 0.1)"
    fill: bool = True
    tension: float = 0.4

class ReviewVolumeTrendResponse(BaseModel):
    labels: List[str]
    datasets: List[ReviewVolumeTrendDataset]

# Helper para MongoDB queries (podría moverse a utilsdb.py más adelante)
async def get_review_metrics(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
    brand_name: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    countries: Optional[List[str]], # Expecting ISO alpha-2 codes e.g., ["DE", "US"]
    sources_map: Dict
):
    query_filter = {} # Initialize empty query filter

    # Brand name filter (case-insensitive regex)
    if brand_name: # Ensure brand_name is not None or empty before adding to filter
        query_filter["brand_name"] = {"$regex": f"^{re.escape(brand_name)}$", "$options": "i"}
    else:
        # If brand_name is None or empty, we might want to log a warning or not query.
        # For now, an empty query_filter would fetch all brands if brand_name is not provided.
        # This behavior should be reviewed based on requirements if brand_name can be optional.
        # Assuming brand_name is always expected for these metrics.
        logger.warning("get_review_metrics called without a brand_name.")
        # To prevent fetching all data if brand_name is missing, we can return zero metrics:
        # return {"count": 0, "average_sentiment": 0.0} # Or raise an error

    # Date filter
    if start_date and end_date:
        query_filter["date"] = {"$gte": start_date, "$lte": end_date}
    elif end_date: # Only end_date implies a window ending now (or up to that end_date)
        query_filter["date"] = {"$lte": end_date}
    # If only start_date, it implies from start_date to infinity (or handled by end_date default)

    # Country filter (case-insensitive regex for each country)
    if countries:
        country_conditions = []
        for country_code in countries:
            if country_code and len(country_code) == 2: # Basic validation for ISO alpha-2
                 # Each condition is a regex match for a single country
                 country_conditions.append({"country": {"$regex": f"^{re.escape(country_code)}$", "$options": "i"}})
            else:
                logger.warning(f"Invalid country code provided: '{country_code}'. Skipping.")
        
        if country_conditions:
            if len(country_conditions) == 1:
                 # If only one valid country, apply its condition directly to query_filter["country"]
                 query_filter["country"] = country_conditions[0]["country"] 
            else:
                 # If multiple valid countries, use $or
                 query_filter["$or"] = country_conditions
    
    # If after all filters, query_filter is still empty (e.g. no brand_name), it might fetch too much.
    # Add a safeguard if brand_name is mandatory.
    if "brand_name" not in query_filter:
        logger.error("CRITICAL: get_review_metrics about to query without a brand_name filter. Aborting metric calculation for safety.")
        return {"count": 0, "average_sentiment": 0.0}


    total_count = 0
    rating_sum = 0
    rating_docs_count = 0
    
    tasks = []

    async def query_collection(collection_name: str):
        nonlocal total_count, rating_sum, rating_docs_count
        if collection_name in await db.list_collection_names():
            collection = db[collection_name]
            logger.debug(f"Querying collection '{collection_name}' with filter: {query_filter}")
            
            current_docs_cursor = collection.find(query_filter)
            docs_in_period = []
            async for doc in current_docs_cursor:
                docs_in_period.append(doc)
            
            current_period_count = len(docs_in_period)
            total_count += current_period_count
            logger.debug(f"Found {current_period_count} docs in '{collection_name}' for brand '{brand_name}' with current filters.")

            for doc in docs_in_period:
                rating_value = doc.get("rating") 
                if isinstance(rating_value, (int, float)):
                    rating_sum += rating_value
                    rating_docs_count += 1
            return current_period_count
        else:
            logger.warning(f"Collection '{collection_name}' not found in DB.")
            return 0

    for coll_name in sources_map.keys():
        tasks.append(query_collection(coll_name))
    
    await asyncio.gather(*tasks)
    
    avg_rating = (rating_sum / rating_docs_count) if rating_docs_count > 0 else 0.0 # Ensure float for consistency
    
    logger.debug(f"Metrics for brand '{brand_name}': Count={total_count}, AvgRating={avg_rating} (sum={rating_sum}, docs_w_rating={rating_docs_count})")
    return {
        "count": total_count,
        "average_sentiment": avg_rating 
    }

def format_percentage_change(current, previous):
    if previous == 0:
        return "N/A" if current == 0 else "+100.0%" # Or some other indicator for new growth
    change = ((current - previous) / previous) * 100
    return f"{'+' if change >= 0 else ''}{change:.1f}%"

def get_trend(current, previous) -> Literal['up', 'down', 'neutral']:
    if current > previous:
        return 'up'
    elif current < previous:
        return 'down'
    return 'neutral'

@app.get("/api/analytics/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    start_date_str: Optional[str] = Query(None, alias="start_date"),
    end_date_str: Optional[str] = Query(None, alias="end_date"),
    countries: Optional[List[str]] = Query(None),
    quick_filter_type: Optional[str] = Query(None, alias="quickFilterType"), 
    user_data=Depends(get_current_user)
):
    usuario_id = int(user_data["sub"])
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        raise HTTPException(status_code=404, detail="Brand not found for user.")
    
    logger.info(f"Analytics API call: brand='{brand_name}', countries={countries}, start='{start_date_str}', end='{end_date_str}', quickFilter='{quick_filter_type}'")

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.error("MONGODB_URI environment variable not set.")
        raise HTTPException(status_code=500, detail="Database configuration error (URI missing).")
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    try:
        await client.admin.command('ping')
        db = client["Reviews"]

        general_sources_map = {
            "reviews_amazon_gold": {"id": "amazon", "name": "Amazon", "brand_field": "brand_name"},
            "reviews_tripadvisor_gold": {"id": "tripadvisor", "name": "TripAdvisor", "brand_field": "brand_name"},
            "reviews_trustpilot_gold": {"id": "trustpilot", "name": "Trustpilot", "brand_field": "brand_name"},
            "reviews_google_gold": {"id": "mybusiness", "name": "Google", "brand_field": "brand_name"}, # This is for Google My Business reviews
            "reviews_druni_gold": {"id": "druni", "name": "Druni", "brand_field": "brand_name"}
        }
        
        sources_map_for_sentiment = {
            "reviews_google_gold": general_sources_map.get("reviews_google_gold"), # Standard Google reviews
            "reviews_tripadvisor_gold": general_sources_map.get("reviews_tripadvisor_gold"),
            "reviews_trustpilot_gold": general_sources_map.get("reviews_trustpilot_gold"),
            # Corrected collection name here:
            "reviews_google_places_gold": {"id": "google_places", "name": "Google Places", "brand_field": "brand_name"} 
        }
        
        fixed_now_utc = datetime.now(dt_timezone.utc)

        # 1. Total Reviews KPI - Always ALL TIME (respects country filter)
        all_time_total_reviews_data = await get_review_metrics(
            db, brand_name,
            start_date=None, 
            end_date=fixed_now_utc, 
            countries=countries, 
            sources_map=general_sources_map
        )
        total_reviews_kpi = KPIReportItem(
            value=f"{all_time_total_reviews_data['count']:,}",
            change="N/A",
            trend="neutral"
        )

        # Determine current period end date
        current_period_end_dt = fixed_now_utc
        if end_date_str: # If frontend sends an end date, use it
            try:
                current_period_end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59, microsecond=999999)
            except ValueError:
                logger.warning(f"Invalid end_date_str: {end_date_str}. Defaulting to now.")
                # current_period_end_dt remains fixed_now_utc
        
        # Determine current period start date
        # If start_date_str is None or empty, it indicates an "All Time" scenario from frontend perspective for dynamic KPIs
        current_period_start_dt: Optional[datetime] = None
        if start_date_str: 
            try:
                current_period_start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                logger.warning(f"Invalid start_date_str: {start_date_str}. Treating as unspecified start.")
                # current_period_start_dt remains None

        # --- Initialize KPI values ---
        new_reviews_value_str = "N/A"
        new_reviews_change = "N/A"
        new_reviews_trend: Literal['up', 'down', 'neutral'] = "neutral"
        
        avg_sentiment_value_float = 0.0 
        avg_sentiment_change_str = "N/A"
        avg_sentiment_trend: Literal['up', 'down', 'neutral'] = "neutral"

        # --- Logic for different scenarios ---
        # `is_all_time_data_fetch` means the actual data fetching window for Avg Sentiment should be "all time".
        # `disable_comparisons` means the %change fields should be N/A.
        
        is_all_time_data_fetch = not current_period_start_dt # True if start_date_str was None/empty
        disable_comparisons = quick_filter_type == 'all-time' or is_all_time_data_fetch


        if is_all_time_data_fetch:
            # Scenario: "All Time" selected on frontend (start_date_str is None/empty)
            new_reviews_value_str = "N/A" # New Reviews is N/A for "All Time"
            new_reviews_change = "N/A"
            new_reviews_trend = "neutral"

            # Average Sentiment for true "All Time"
            all_time_avg_sentiment_data = await get_review_metrics(
                db, brand_name,
                None, # Explicitly None for start_date for true "All Time" calculation
                current_period_end_dt, # Use the determined end date
                countries, sources_map_for_sentiment
            )
            avg_sentiment_value_float = all_time_avg_sentiment_data["average_sentiment"]
            avg_sentiment_change_str = "N/A" # No comparison for "All Time"
            if avg_sentiment_value_float > 0:
                if avg_sentiment_value_float >= 3.5: avg_sentiment_trend = 'up'
                elif avg_sentiment_value_float < 2.5: avg_sentiment_trend = 'down'
                else: avg_sentiment_trend = 'neutral'
            else:
                avg_sentiment_trend = 'neutral'

        elif current_period_start_dt and current_period_end_dt: # Specific date range provided (not "All Time" data fetch)
            start_for_calculation = current_period_start_dt
            end_for_calculation = current_period_end_dt
            
            # New Reviews - Current Period
            new_reviews_current_data = await get_review_metrics(db, brand_name, start_for_calculation, end_for_calculation, countries, general_sources_map)
            new_reviews_current_count = new_reviews_current_data["count"]
            new_reviews_value_str = f"{new_reviews_current_count:,}"

            # Average Sentiment - Current Period
            avg_sentiment_current_data = await get_review_metrics(db, brand_name, start_for_calculation, end_for_calculation, countries, sources_map_for_sentiment)
            avg_sentiment_value_float = avg_sentiment_current_data["average_sentiment"]

            if not disable_comparisons: # Perform comparisons only if not explicitly an "all-time" quick filter
                period_duration = end_for_calculation - start_for_calculation
                if period_duration.total_seconds() <= 0: period_duration = timedelta(days=7) # Fallback

                previous_period_end_dt = start_for_calculation - timedelta(microseconds=1)
                previous_period_start_dt = previous_period_end_dt - period_duration
                
                # New Reviews - Previous Period for comparison
                new_reviews_previous_data = await get_review_metrics(db, brand_name, previous_period_start_dt, previous_period_end_dt, countries, general_sources_map)
                new_reviews_previous_count = new_reviews_previous_data["count"]
                new_reviews_change = format_percentage_change(new_reviews_current_count, new_reviews_previous_count)
                new_reviews_trend = get_trend(new_reviews_current_count, new_reviews_previous_count)

                # Average Sentiment - Previous Period for comparison
                avg_sentiment_previous_data = await get_review_metrics(db, brand_name, previous_period_start_dt, previous_period_end_dt, countries, sources_map_for_sentiment)
                avg_sentiment_previous = avg_sentiment_previous_data["average_sentiment"]

                if avg_sentiment_previous > 0:
                    abs_change = avg_sentiment_value_float - avg_sentiment_previous
                    avg_sentiment_change_str = f"{'+' if abs_change >= 0 else ''}{abs_change:.1f}"
                    avg_sentiment_trend = get_trend(avg_sentiment_value_float, avg_sentiment_previous)
                elif avg_sentiment_value_float > 0:
                    avg_sentiment_change_str = "New"
                    avg_sentiment_trend = 'up'
            
            # Fallback trend determination for current period if no comparison was made but value exists
            if disable_comparisons or avg_sentiment_change_str == "N/A":
                if avg_sentiment_value_float > 0:
                    if avg_sentiment_value_float >= 3.5: avg_sentiment_trend = 'up'
                    elif avg_sentiment_value_float < 2.5: avg_sentiment_trend = 'down'
                    else: avg_sentiment_trend = 'neutral'
                else:
                     avg_sentiment_trend = 'neutral'
        else: 
            # Fallback for truly ambiguous ranges (e.g. only end_date but not 'all-time' and no start_date)
            logger.warning(f"Analytics overview: Ambiguous or incomplete date range. start='{start_date_str}', end='{end_date_str}', quickFilter='{quick_filter_type}'. Defaulting KPIs to N/A.")
            # Values already initialized to N/A or 0.0 which results in N/A display

        # Construct KPI items
        new_reviews_kpi = KPIReportItem(value=new_reviews_value_str, change=new_reviews_change, trend=new_reviews_trend)
        average_sentiment_kpi = KPIReportItem(value=f"{avg_sentiment_value_float:.1f}" if avg_sentiment_value_float > 0 else "N/A", change=avg_sentiment_change_str, trend=avg_sentiment_trend)
        
        last_updated_kpi = KPIReportItem(
            value=f"As of {fixed_now_utc.strftime('%b %d, %H:%M')} UTC",
            change="Real-time data", 
            trend='neutral'
        )

        return AnalyticsOverviewResponse(
            totalReviews=total_reviews_kpi,
            newReviews7d=new_reviews_kpi,
            averageSentiment=average_sentiment_kpi,
            lastUpdated=last_updated_kpi
        )

    except ServerSelectionTimeoutError as e: # Changed this line
        logger.error(f"MongoDB ServerSelectionTimeoutError: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Database connection timeout: {str(e)}")
    except Exception as e:
        logger.error(f"Error in get_analytics_overview: {e}", exc_info=True)
        if isinstance(e, HTTPException): # Re-raise existing HTTPExceptions
            raise e
        raise HTTPException(status_code=500, detail=f"Internal server error processing analytics: {str(e)}")

    finally:
        if 'client' in locals() and client: 
            client.close()
            logger.info("MongoDB connection closed.")
        # else:
            # logger.warning("Client was None or not defined in finally block, no connection to close.")

@app.get("/api/analytics/review-volume-trend", response_model=ReviewVolumeTrendResponse)
async def get_review_volume_trend(
    start_date_str: Optional[str] = Query(None, alias="start_date"),
    end_date_str: Optional[str] = Query(None, alias="end_date"),
    countries: Optional[List[str]] = Query(None),
    user_data=Depends(get_current_user)
):
    usuario_id = int(user_data["sub"])
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found for user.")

    logger.info(f"Review volume trend request: brand='{brand_name}', countries={countries}, start='{start_date_str}', end='{end_date_str}'")

    fixed_now_utc = datetime.now(dt_timezone.utc)
    
    try:
        if end_date_str:
            effective_end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            effective_end_dt = fixed_now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)

        if start_date_str:
            effective_start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to 6 months prior to end_date (for 6 data points ending in effective_end_dt's month)
            temp_start_dt = effective_end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for _ in range(5): # Go back 5 full months to get a 6-month range
                first_of_prev_month = temp_start_dt - timedelta(days=1) # Go to end of previous month
                temp_start_dt = first_of_prev_month.replace(day=1) # Go to start of that previous month
            effective_start_dt = temp_start_dt
            
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format provided.")

    if effective_start_dt > effective_end_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be after end date.")

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.error("MONGODB_URI environment variable not set for review volume trend.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database configuration error.")

    client = None
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        db = client["Reviews"]

        # Define sources and their specific brand/country field names if they differ
        general_sources_map = {
            "reviews_amazon_gold": {"id": "amazon", "name": "Amazon", "brand_field": "brand_name", "country_field": "country"},
            "reviews_tripadvisor_gold": {"id": "tripadvisor", "name": "TripAdvisor", "brand_field": "brand_name", "country_field": "country"},
            "reviews_trustpilot_gold": {"id": "trustpilot", "name": "Trustpilot", "brand_field": "brand_name", "country_field": "country"},
            "reviews_google_gold": {"id": "mybusiness", "name": "Google", "brand_field": "brand_name", "country_field": "country"},
            "reviews_druni_gold": {"id": "druni", "name": "Druni", "brand_field": "brand_name", "country_field": "country"}
        }

        date_range_days = (effective_end_dt - effective_start_dt).days
        use_weekly_granularity = date_range_days < 60  # 2 months = ~60 days

        aggregated_counts = defaultdict(int)

        for collection_name, source_info in general_sources_map.items():
            if collection_name not in await db.list_collection_names():
                logger.debug(f"Collection '{collection_name}' not found for trend. Skipping.")
                continue

            collection = db[collection_name]
            # Base query filter
            query_filter = {
                source_info["brand_field"]: {"$regex": f"^{re.escape(brand_name)}$", "$options": "i"},
                "date": {"$gte": effective_start_dt, "$lte": effective_end_dt}
            }

            # Country filter
            if countries:
                country_conditions = []
                country_field_name = source_info.get("country_field", "country") 
                for country_code in countries:
                    if country_code and len(country_code) == 2: # Basic ISO alpha-2 validation
                        country_conditions.append({country_field_name: {"$regex": f"^{re.escape(country_code)}$", "$options": "i"}})
                if country_conditions:
                    if len(country_conditions) == 1:
                        query_filter.update(country_conditions[0])
                    else:
                        query_filter["$or"] = country_conditions
            
            if use_weekly_granularity:
                pipeline = [
                    {"$match": query_filter},
                    {"$project": {
                        "year": {"$year": "$date"},
                        "week": {"$week": "$date"},
                        "date": "$date"
                    }},
                    {"$group": {
                        "_id": {
                            "year": "$year",
                            "week": "$week"
                        },
                        "count": {"$sum": 1},
                        "start_date": {"$min": "$date"}
                    }},
                    {"$sort": {"start_date": 1}}
                ]
            else:
                pipeline = [
                    {"$match": query_filter},
                    {"$project": {"year": {"$year": "$date"}, "month": {"$month": "$date"}}},
                    {"$group": {"_id": {"year": "$year", "month": "$month"}, "count": {"$sum": 1}}}
                ]
            results = await collection.aggregate(pipeline).to_list(length=None)
            for res in results:
                aggregated_counts[(res["_id"]["year"], res["_id"]["week"] if use_weekly_granularity else res["_id"]["month"])] += res["count"]
        
        chart_labels = []
        chart_data = []
        
        current_dt = effective_start_dt.replace(day=1)
        # Ensure loop end condition correctly includes the last month of the period
        loop_end_boundary = effective_end_dt.replace(day=1)

        cumulative_count = 0
        for date_key in sorted(aggregated_counts.keys()):
            cumulative_count += aggregated_counts[date_key]
            chart_data.append(cumulative_count)
            if use_weekly_granularity:
                chart_labels.append(f"Week {date_key[1]}")
            else:
                chart_labels.append(datetime(date_key[0], date_key[1], 1).strftime("%b"))

        return ReviewVolumeTrendResponse(labels=chart_labels, datasets=[ReviewVolumeTrendDataset(data=chart_data)])

    except ServerSelectionTimeoutError as e: # Specific exception for connection issues
        logger.error(f"MongoDB ServerSelectionTimeoutError for trend: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Database connection timeout: {str(e)}")
    except Exception as e:
        logger.error(f"Error in get_review_volume_trend: {e}", exc_info=True)
        if isinstance(e, HTTPException): # Re-raise if it's already an HTTPException
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing review volume trend.")
    finally:
        if client:
            client.close()

@app.get("/api/analytics/sentiment-distribution")
async def get_sentiment_distribution(
    start_date_str: Optional[str] = Query(None, alias="start_date"),
    end_date_str: Optional[str] = Query(None, alias="end_date"),
    countries: Optional[List[str]] = Query(None),
    user_data=Depends(get_current_user)
):
    from collections import defaultdict
    usuario_id = int(user_data["sub"])
    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        raise HTTPException(status_code=404, detail="Brand not found for user.")

    fixed_now_utc = datetime.now(dt_timezone.utc)
    try:
        if end_date_str:
            effective_end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            effective_end_dt = fixed_now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)

        if start_date_str:
            effective_start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            temp_start_dt = effective_end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for _ in range(5):
                first_of_prev_month = temp_start_dt - timedelta(days=1)
                temp_start_dt = first_of_prev_month.replace(day=1)
            effective_start_dt = temp_start_dt

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format provided.")

    if effective_start_dt > effective_end_dt:
        raise HTTPException(status_code=400, detail="Start date cannot be after end date.")

    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise HTTPException(status_code=500, detail="Database configuration error.")

    client = None
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        db = client["Reviews"]

        general_sources_map = {
            "reviews_amazon_gold": {"brand_field": "brand_name", "country_field": "country"},
            "reviews_tripadvisor_gold": {"brand_field": "brand_name", "country_field": "country"},
            "reviews_trustpilot_gold": {"brand_field": "brand_name", "country_field": "country"},
            "reviews_google_gold": {"brand_field": "brand_name", "country_field": "country"},
            "reviews_druni_gold": {"brand_field": "brand_name", "country_field": "country"}
        }

        date_range_days = (effective_end_dt - effective_start_dt).days
        use_weekly_granularity = date_range_days < 60

        sentiment_map = {
            "positivo": "Positive",
            "positive": "Positive",
            "neutro": "Neutral",
            "neutral": "Neutral",
            "negativo": "Negative",
            "negative": "Negative"
        }
        sentiment_keys = ["Positive", "Neutral", "Negative"]

        period_sentiment_counts = defaultdict(lambda: {k: 0 for k in sentiment_keys})

        for collection_name, source_info in general_sources_map.items():
            if collection_name not in await db.list_collection_names():
                continue

            collection = db[collection_name]
            query_filter = {
                source_info["brand_field"]: {"$regex": f"^{re.escape(brand_name)}$", "$options": "i"},
                "date": {"$gte": effective_start_dt, "$lte": effective_end_dt}
            }
            if countries:
                country_conditions = []
                country_field_name = source_info.get("country_field", "country")
                for country_code in countries:
                    if country_code and len(country_code) == 2:
                        country_conditions.append({country_field_name: {"$regex": f"^{re.escape(country_code)}$", "$options": "i"}})
                if country_conditions:
                    if len(country_conditions) == 1:
                        query_filter.update(country_conditions[0])
                    else:
                        query_filter["$or"] = country_conditions

            if use_weekly_granularity:
                pipeline = [
                    {"$match": query_filter},
                    {"$project": {
                        "year": {"$year": "$date"},
                        "week": {"$week": "$date"},
                        "sentiment": 1
                    }},
                    {"$group": {
                        "_id": {
                            "year": "$year",
                            "week": "$week",
                            "sentiment": "$sentiment"
                        },
                        "count": {"$sum": 1}
                    }}
                ]
            else:
                pipeline = [
                    {"$match": query_filter},
                    {"$project": {
                        "year": {"$year": "$date"},
                        "month": {"$month": "$date"},
                        "sentiment": 1
                    }},
                    {"$group": {
                        "_id": {
                            "year": "$year",
                            "month": "$month",
                            "sentiment": "$sentiment"
                        },
                        "count": {"$sum": 1}
                    }}
                ]
            results = await collection.aggregate(pipeline).to_list(length=None)
            for res in results:

                if use_weekly_granularity:
                    period_key = (res["_id"]["year"], res["_id"]["week"])
                else:
                    period_key = (res["_id"]["year"], res["_id"]["month"])
                # Normalize sentiment value
                raw_sentiment = res["_id"].get("sentiment") # Use .get() for safety
                if isinstance(raw_sentiment, str):
                    normalized = raw_sentiment.strip().lower()
                else:
                    normalized = "neutral"
                sentiment = sentiment_map.get(normalized, "Neutral")
                period_sentiment_counts[period_key][sentiment] += res["count"]

        sorted_periods = sorted(period_sentiment_counts.keys())
        labels = []
        data = {k: [] for k in sentiment_keys}
        for period in sorted_periods:
            year, period_val = period
            if use_weekly_granularity:
                labels.append(f"Week {period_val}")
            else:
                labels.append(datetime(year, period_val, 1).strftime("%b"))
            total = sum(period_sentiment_counts[period].values())
            for k in sentiment_keys:
                percent = (period_sentiment_counts[period][k] / total * 100) if total > 0 else 0
                data[k].append(round(percent, 2))

        return {
            "labels": labels,
            "datasets": [
                {"label": "Positive", "data": data["Positive"], "backgroundColor": "#10B981"},
                {"label": "Neutral", "data": data["Neutral"], "backgroundColor": "#6B7280"},
                {"label": "Negative", "data": data["Negative"], "backgroundColor": "#EF4444"},
            ]
        }
    finally:
        if client:
            client.close()

# Define a Pydantic model for the response items
class SourceStatisticItem(BaseModel):
    id: str
    name: str
    reviewCount: int
    avgSentiment: float # Will be 0.0 if no reviews with ratings

@app.get("/api/analytics/source-statistics", response_model=List[SourceStatisticItem])
async def get_source_statistics(
    start_date_str: Optional[str] = Query(None, alias="start_date"),
    end_date_str: Optional[str] = Query(None, alias="end_date"),
    countries: Optional[List[str]] = Query(None),
    user_data = Depends(get_current_user)
):
    usuario_id = int(user_data["sub"])
    logger.info(f"Fetching source statistics for user {usuario_id}, start: {start_date_str}, end: {end_date_str}, countries: {countries}")

    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found for user.")

    effective_start_dt: Optional[datetime] = None
    effective_end_dt: Optional[datetime] = None
    try:
        if start_date_str:
            effective_start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date_str:
            effective_end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format provided.")

    if effective_start_dt and effective_end_dt and effective_start_dt > effective_end_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be after end date.")

    client = None
    try:
        mongodb_uri = os.getenv("MONGODB_URI")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_uri) # Use async client
        db = client["Reviews"]

        source_mappings = {
            "reviews_google_gold": {"id": "google", "name": "Google", "brand_field": "brand_name", "country_field": "country", "rating_field": "rating"},
            "reviews_amazon_gold": {"id": "amazon", "name": "Amazon", "brand_field": "brand_name", "country_field": "country", "rating_field": "rating"},
            "reviews_trustpilot_gold": {"id": "trustpilot", "name": "Trustpilot", "brand_field": "brand_name", "country_field": "country", "rating_field": "rating"},
            "reviews_tripadvisor_gold": {"id": "tripadvisor", "name": "TripAdvisor", "brand_field": "brand_name", "country_field": "country", "rating_field": "rating"},
            "reviews_druni_gold": {"id": "druni", "name": "Druni", "brand_field": "brand_name", "country_field": "country", "rating_field": "rating"}
        }

        results = []
        
        for coll_name, info in source_mappings.items():
            if coll_name not in await db.list_collection_names():
                # If collection doesn't exist, add with 0 count and 0.0 sentiment
                results.append(SourceStatisticItem(id=info["id"], name=info["name"], reviewCount=0, avgSentiment=0.0))
                logger.warning(f"Collection {coll_name} not found. Reporting 0 stats for source {info['name']}.")
                continue

            collection = db[coll_name]
            brand_field = info["brand_field"]
            country_field = info.get("country_field", "country")
            rating_field = info.get("rating_field", "rating") # Assume 'rating' is the field name

            match_conditions = {brand_field: {"$regex": f"^{re.escape(brand_name)}$", "$options": "i"}} if brand_name else {}

            date_conditions = {}
            if effective_start_dt:
                date_conditions["$gte"] = effective_start_dt
            if effective_end_dt:
                date_conditions["$lte"] = effective_end_dt
            if date_conditions:
                match_conditions["date"] = date_conditions
            
            if countries:
                uppercase_countries = [c.upper() for c in countries]
                match_conditions[country_field] = {"$in": uppercase_countries}

            # MongoDB aggregation pipeline
            pipeline = [
                {"$match": match_conditions},
                {"$group": {
                    "_id": None, # Group all matching documents
                    "reviewCount": {"$sum": 1},
                    "totalRating": {"$sum": f"${rating_field}"}, # Sum the rating field
                    "ratingDocsCount": {"$sum": {"$cond": [{"$ifNull": [f"${rating_field}", False]}, 1, 0]}} # Count docs with a rating
                }}
            ]
            
            logger.debug(f"Aggregation pipeline for {coll_name}: {pipeline}")
            
            aggregation_result = await collection.aggregate(pipeline).to_list(length=1)
            
            review_count = 0
            avg_sentiment = 0.0

            if aggregation_result:
                res = aggregation_result[0]
                review_count = res.get("reviewCount", 0)
                total_rating = res.get("totalRating", 0)
                rating_docs_count = res.get("ratingDocsCount", 0)
                if rating_docs_count > 0:
                    avg_sentiment = total_rating / rating_docs_count
            
            results.append(SourceStatisticItem(
                id=info["id"], 
                name=info["name"], 
                reviewCount=review_count, 
                avgSentiment=round(avg_sentiment, 2) # Round to 2 decimal places
            ))

        logger.info(f"Source statistics for brand {brand_name}: {results}")
        return results
    except Exception as e:
        logger.error(f"Error getting source statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch source statistics: {str(e)}")
    finally:
        if client:
            client.close()

# Define Pydantic models for the Latest Comments response
class LatestCommentItem(BaseModel):
    countryCode: Optional[str] = None
    name: Optional[str] = None
    sourceId: str # e.g., "google", "amazon" - for frontend mapping
    sourceDisplayName: str # e.g. "Google", "Amazon" - direct from backend mapping
    date: datetime
    comment: Optional[str] = None
    sentiment: Optional[str] = None

@app.get("/api/analytics/latest-comments", response_model=List[LatestCommentItem])
async def get_latest_comments(
    countries: Optional[List[str]] = Query(None),
    user_data = Depends(get_current_user)
):
    usuario_id = int(user_data["sub"])
    logger.info(f"INSIGHTS-API: get_latest_comments called. Received countries: {countries}")

    brand_name = get_marca_name_by_id(usuario_id)
    if not brand_name:
        logger.error("INSIGHTS-API: get_latest_comments - Brand not found for user.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found for user.")
    logger.info(f"INSIGHTS-API: get_latest_comments - Operating for brand: {brand_name}")

    client = None
    try:
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            logger.error("INSIGHTS-API: get_latest_comments - MONGODB_URI not set.")
            raise HTTPException(status_code=500, detail="Database configuration error")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_uri)
        db = client["Reviews"] # Assuming your reviews are in the "Reviews" database

        # Updated source configurations with more specific field names
        source_configs = {
            "reviews_google_gold": {
                "id": "google", "displayName": "Google Reviews",
                "brand_field": "brand_name", "country_field": "country",
                "date_field": "date", "author_field": "author_name", 
                "comment_field": "review",       # Standardized to 'review'
                "sentiment_field": "sentiment"
            },
            "reviews_amazon_gold": {
                "id": "amazon", "displayName": "Amazon",
                "brand_field": "brand_name", "country_field": "country", 
                "date_field": "date", "author_field": "author_name", 
                "comment_field": "review",       # Standardized to 'review'
                "sentiment_field": "sentiment"
            },
            "reviews_trustpilot_gold": {
                "id": "trustpilot", "displayName": "Trustpilot",
                "brand_field": "brand_name", "country_field": "country", 
                "date_field": "date", "author_field": "author_name", 
                "comment_field": "review",       # Standardized to 'review'
                "sentiment_field": "sentiment"
            },
            "reviews_tripadvisor_gold": {
                "id": "tripadvisor", "displayName": "TripAdvisor",
                "brand_field": "brand_name", "country_field": "country", 
                "date_field": "date", "author_field": "author_name", 
                "comment_field": "review",       # Standardized to 'review'
                "sentiment_field": "sentiment"
            },
            "reviews_druni_gold": {
                "id": "druni", "displayName": "Druni",
                "brand_field": "brand_name", "country_field": "country", 
                "date_field": "date", "author_field": "author_name", 
                "comment_field": "review",       # Standardized to 'review'
                "sentiment_field": "sentiment"
            }
        }
        
        all_comments = []
        # Fetch a bit more from each source to ensure we get 5 overall after global sorting
        limit_per_source = 10 

        for coll_name, config in source_configs.items():
            if coll_name not in await db.list_collection_names():
                logger.warning(f"INSIGHTS-API: get_latest_comments - Collection {coll_name} not found. Skipping.")
                continue

            collection = db[coll_name]
            
            # Base query filter: case-insensitive brand_name matching
            query_filter = {}
            if brand_name and config.get("brand_field"):
                 query_filter[config["brand_field"]] = {"$regex": f"^{re.escape(brand_name)}$", "$options": "i"}
            else:
                logger.warning(f"INSIGHTS-API: get_latest_comments - No brand_name or brand_field configured for {coll_name}. Querying all documents (if no other filters).")


            # Country filter: case-insensitive matching for each country code
            if countries and config.get("country_field"):
                # Assuming frontend sends ISO alpha-2 codes. Normalize to uppercase for consistent matching.
                normalized_countries = [c.upper() for c in countries if c and len(c) == 2]
                if normalized_countries:
                    query_filter[config["country_field"]] = {"$in": normalized_countries}
                logger.info(f"INSIGHTS-API: get_latest_comments - Filtering {coll_name} by countries: {normalized_countries}")
            
            logger.debug(f"INSIGHTS-API: get_latest_comments - Querying {coll_name} with filter: {query_filter}")

            try:
                # Fetch recent documents sorted by date
                # Ensure the date_field exists and is sortable (BSON Date type preferred)
                date_sort_field = config.get("date_field", "date") # Default to "date" if not specified

                cursor = collection.find(query_filter).sort(date_sort_field, -1).limit(limit_per_source)
                async for doc in cursor:
                    doc_date = doc.get(date_sort_field)
                    if isinstance(doc_date, str):
                        try:
                            # Attempt to parse ISO format, handling 'Z' for UTC
                            doc_date = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                        except ValueError:
                            logger.warning(f"INSIGHTS-API: get_latest_comments - Could not parse date string '{doc_date}' from {coll_name} for doc {doc.get('_id')}. Skipping.")
                            continue 
                    elif not isinstance(doc_date, datetime):
                         logger.warning(f"INSIGHTS-API: get_latest_comments - Date field '{date_sort_field}' is not a datetime object or parsable string in {coll_name} for doc {doc.get('_id')}. Type: {type(doc_date)}. Skipping.")
                         continue
                    
                    # Safely get comment, author name, country code, and sentiment
                    comment_text = doc.get(config.get("comment_field", "comment")) # Default to "comment" if not specified
                    author_name = doc.get(config.get("author_field")) # No default, will be None if field missing or key not in config
                    country_val = doc.get(config.get("country_field"))
                    country_code_final = str(country_val).lower() if country_val else None # Ensure lowercase, allow None

                    raw_sentiment = doc.get(config.get("sentiment_field", "sentiment")) # Default to "sentiment"
                    processed_sentiment = str(raw_sentiment).lower() if raw_sentiment is not None else None

                    all_comments.append(LatestCommentItem(
                        countryCode=country_code_final,
                        name=author_name,
                        sourceId=config["id"],
                        sourceDisplayName=config["displayName"],
                        date=doc_date,
                        comment=comment_text,
                        sentiment=processed_sentiment
                    ))
            except Exception as e_fetch:
                 logger.error(f"INSIGHTS-API: get_latest_comments - Error fetching/processing from {coll_name}: {e_fetch}", exc_info=True)

        # Sort all collected comments by date (descending)
        # Filter out comments that ended up with a None date due to parsing issues before sorting
        valid_comments = [c for c in all_comments if c.date is not None]
        valid_comments.sort(key=lambda c: c.date, reverse=True)
        
        # Get the top 5 overall
        latest_five_comments = valid_comments[:5]
        
        logger.info(f"INSIGHTS-API: get_latest_comments - Returning {len(latest_five_comments)} latest comments for brand {brand_name} after processing all sources.")
        logger.info(f"INSIGHTS-API: get_latest_comments - Latest comments: {latest_five_comments}")
        if latest_five_comments:
            logger.debug(f"INSIGHTS-API: get_latest_comments - First comment details: {latest_five_comments[0].model_dump_json(indent=2)}")
        return latest_five_comments

    except ServerSelectionTimeoutError as e:
        logger.error(f"INSIGHTS-API: get_latest_comments - MongoDB ServerSelectionTimeoutError: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Database connection timeout: {str(e)}")
    except Exception as e:
        logger.error(f"INSIGHTS-API: get_latest_comments - Unexpected error: {e}", exc_info=True)
        # Avoid raising HTTPException if it's already one
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest comments due to an internal server error: {str(e)}")
    finally:
        if client:
            client.close()
            logger.info("INSIGHTS-API: get_latest_comments - MongoDB connection closed.")

async def _run_report_generation_logic(
    task_id: str,
    report_request: ReportRequest,
    usuario_id: int,
    brand_name: str
    # event_queue: asyncio.Queue # REMOVED - Redis Pub/Sub handles this
):
    try:
        logger.info(f"Task [{task_id}] - _run_report_generation_logic AT START for brand '{brand_name}', type '{report_request.report_type}'")
        
        await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "starting", "message": "Report generation process started."})

        # 1. Consultar reviews con filtros
        await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "fetching_reviews", "message": "Fetching review data..."})
        start_date_str = report_request.start_date.isoformat() + 'Z' if report_request.start_date else None
        end_date_str = report_request.end_date.isoformat() + 'Z' if report_request.end_date else None

        reviews_data = await query_reviews_for_report_async(
            start_date=start_date_str,
            end_date=end_date_str,
            sources=report_request.sources,
            countries=report_request.countries,
            brand_name=brand_name
        )
        logger.info(f"Task [{task_id}] - Reviews data fetched: {len(reviews_data)} entries")
        await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "reviews_fetched", "message": f"Found {len(reviews_data)} reviews."})

        # 2. Obtener detalles del arquetipo
        archetype_details = None
        if report_request.archetype_id and report_request.archetype_id != 'all':
            await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "fetching_archetype", "message": f"Fetching archetype details for {report_request.archetype_id}..."})
            try:
                archetype_details = await asyncio.to_thread(fetch_single_archetype_details, brand_name, report_request.archetype_id)
                if archetype_details:
                    logger.info(f"Task [{task_id}] - Archetype details fetched: {archetype_details.get('name')}")
                    await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "archetype_fetched", "message": f"Archetype '{archetype_details.get('name')}' loaded."})
                else:
                    logger.warning(f"Task [{task_id}] - Archetype '{report_request.archetype_id}' not found for brand '{brand_name}'.")
                    await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "archetype_not_found", "message": f"Archetype '{report_request.archetype_id}' not found."})
            except Exception as arch_error:
                logger.error(f"Task [{task_id}] - Error fetching archetype details: {arch_error}", exc_info=True)
                await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "archetype_error", "message": "Error fetching archetype details."})
                archetype_details = None # Ensure it's None on error

        # 3. Procesar productos si es necesario (existing logic)
        products_list = report_request.products if report_request.report_type == 'top-flop-products' else None

        # 4. Generar contenido HTML del informe
        await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "generating_html", "message": "Generating report HTML..."})
        html_content = None
        if not reviews_data and report_request.report_type != 'content-calendar':
            logger.warning(f"Task [{task_id}] - No reviews found for the specified filters for brand {brand_name}")
            # Ensure render_html_report is thread-safe if it has side effects or uses shared non-thread-safe resources.
            # Assuming it's primarily CPU-bound or safe for asyncio.to_thread.
            html_content = await asyncio.to_thread(
                render_html_report, 
                title=f"Empty Report - {report_request.report_type}",
                intro="No reviews were found matching the filter criteria.",
                secciones=[("Data", "<p>No data available to generate this report with the selected filters.</p>")],
                imagenes=[]
            )
            await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "empty_report", "message": "No data found, empty report generated."})
        else:
            try:
                # Assuming generar_informe_por_tipo is potentially CPU-bound or involves blocking I/O
                html_content = await asyncio.to_thread(
                    generar_informe_por_tipo,
                    reviews_data=reviews_data,
                    report_type=report_request.report_type,
                    archetype_details=archetype_details,
                    products_list=products_list
                )
                if not html_content or "Error - Informe" in html_content: # Check for known error markers
                    logger.error(f"Task [{task_id}] - Error during HTML content generation for report '{report_request.report_type}'. Content: {html_content[:200] if html_content else 'None'}")
                    await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "generation_error", "message": "Error occurred during HTML generation."})
                    html_content = None # Ensure html_content is None if generation failed critically
                else:
                    logger.info(f"Task [{task_id}] - HTML content generated successfully.")
                    await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "html_generated", "message": "Report HTML generated."})

            except ValueError as report_error: # Catch invalid/unimplemented type errors specifically
                logger.error(f"Task [{task_id}] - ValueError during report generation: {report_error}", exc_info=True)
                await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "failed", "error": str(report_error), "message": f"Report generation failed: {report_error}"})
                return # Exit if generation failed
            except Exception as gen_error:
                logger.error(f"Task [{task_id}] - Unexpected error during report generation: {gen_error}", exc_info=True)
                await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "failed", "error": str(gen_error), "message": "An unexpected error occurred during report generation."})
                return # Exit if generation failed

        # 5. Guardar el informe en MongoDB
        if html_content is not None: # Only proceed if HTML content was generated
            await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "saving_report", "message": "Saving report to database..."})
            try:
                filters_dict = report_request.model_dump() # Using Pydantic's model_dump
                identifier_to_save = 'General'
                if archetype_details and archetype_details.get('name'):
                    identifier_to_save = archetype_details['name']
                elif report_request.archetype_id and report_request.archetype_id != 'all':
                    identifier_to_save = report_request.archetype_id

                # Assuming save_report_to_mongodb involves I/O
                save_success = await asyncio.to_thread(
                    save_report_to_mongodb,
                    brand_name=brand_name,
                    report_type=report_request.report_type,
                    html_content=html_content,
                    filters=filters_dict,
                    user_id=usuario_id,
                    archetype_identifier=identifier_to_save,
                    archetype_full_details=archetype_details # Pass full details
                )
                if save_success:
                    logger.info(f"Task [{task_id}] - Report saved to MongoDB successfully.")
                    await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "report_saved", "message": "Report saved to database."})
                else:
                    logger.warning(f"Task [{task_id}] - Failed to save report to MongoDB (save_report_to_mongodb returned False/None).")
                    await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "save_failed", "message": "Failed to save report to database."})
            except Exception as mongo_save_error:
                logger.error(f"Task [{task_id}] - Error saving report to MongoDB: {mongo_save_error}", exc_info=True)
                await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "save_error", "message": "Error saving report to database."})
        elif report_request.report_type != 'content-calendar' and not reviews_data: # No data for report (and not content-calendar)
             logger.info(f"Task [{task_id}] - Report generation skipped saving as there was no data and html_content indicates empty report.")
        elif html_content is None : # Generation failed before this point
             logger.warning(f"Task [{task_id}] - Report not saved to MongoDB because HTML content generation failed or was null.")


        # 6. Finalizar
        final_status_val = "completed"
        final_message = "Report generation completed successfully."

        if html_content is None : # If html_content is None, it means generation failed or was skipped (e.g. for no data if not handled properly)
            final_status_val = "failed"
            final_message = "Report generation failed or produced no content."
        elif "Error - Informe" in html_content:
            final_status_val = "failed" # Or "completed_with_errors" if you prefer more granularity
            final_message = "Report generation completed with an error in content."
        elif "Empty Report" in html_content : # Check for empty report marker
            final_message = "Report generation completed: No data found."
            # Status can remain "completed" if an empty report is a valid outcome

        final_event_data = {
            "status": final_status_val,
            "message": final_message,
            # Send HTML content only on success, or a placeholder on failure.
            # Be cautious about sending large HTML content via SSE if it's very large.
            # Consider sending a URL or a flag to fetch it separately.
            # For now, keeping previous behavior but it's a point of optimization.
            "html_content": html_content if final_status_val == "completed" and html_content else "<html><body>Error: No content generated or generation failed.</body></html>",
            "brand_name": brand_name,
            "report_type": report_request.report_type,
            "task_id": task_id # Include task_id in the final event
        }
        await sse_dispatch_event(_redis_pool, task_id, "report_generation", final_event_data)
        logger.info(f"Task [{task_id}] - Report generation process finished with status: {final_status_val}.")

    except Exception as e:
        logger.error(f"Task [{task_id}] - Unhandled exception in _run_report_generation_logic: {e}", exc_info=True)
        try:
            # Ensure task_id is in the error payload
            await sse_dispatch_event(_redis_pool, task_id, "report_generation", {"status": "failed", "error": str(e), "task_id": task_id, "message": "A critical error occurred during report generation."})
        except Exception as q_e: # Error trying to send the error event
            logger.error(f"Task [{task_id}] - CRITICAL: Failed to send final error SSE event after unhandled exception: {q_e}", exc_info=True)
    finally:
        logger.info(f"Task [{task_id}] - _run_report_generation_logic finished execution (status should have been sent).")


# ++ NEW: Unified SSE Streaming Endpoint with Redis Pub/Sub ++
@app.get("/api/sse/stream")
async def multiplexed_sse_stream(
    request: Request,
    subscribe_task_ids: Optional[str] = Query(None, description="Comma-separated task_ids for report/archetype generation events"),
    subscribe_job_ids: Optional[str] = Query(None, description="Comma-separated job_ids for scraping events"),
    subscribe_brand_events: Optional[str] = Query(None, description="Comma-separated brand-specific event keys, e.g., for archetype updates"),
    subscribe_discovery_ids: Optional[str] = Query(None, description="Comma-separated snapshot_ids for Amazon product discovery events"), # New parameter
    subscribe_manual_lookup_ids: Optional[str] = Query(None, description="Comma-separated snapshot_ids for manual product lookup events"),
    subscribe_trustpilot_discovery_ids: Optional[str] = Query(None, description="Comma-separated task_ids for Trustpilot discovery events"),
    subscribe_tripadvisor_discovery_ids: Optional[str] = Query(None, description="Comma-separated task_ids for TripAdvisor discovery events"),
    subscribe_google_places_discovery_ids: Optional[str] = Query(None, description="Comma-separated task_ids for Google Places discovery events"),
):
    global _redis_pool
    if not _redis_pool:
        logger.error("SSE Stream Endpoint: Redis pool is not available. SSE will not function.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSE service temporarily unavailable due to Redis connection issue.")

    event_ids_to_subscribe = []
    if subscribe_task_ids:
        event_ids_to_subscribe.extend([tid.strip() for tid in subscribe_task_ids.split(',') if tid.strip()])
    if subscribe_job_ids:
        event_ids_to_subscribe.extend([jid.strip() for jid in subscribe_job_ids.split(',') if jid.strip()])
    if subscribe_brand_events: 
        event_ids_to_subscribe.extend([key.strip() for key in subscribe_brand_events.split(',') if key.strip()])
    if subscribe_discovery_ids: # Process the new parameter
        event_ids_to_subscribe.extend([did.strip() for did in subscribe_discovery_ids.split(',') if did.strip()])
    if subscribe_manual_lookup_ids:
        event_ids_to_subscribe.extend([sid.strip() for sid in subscribe_manual_lookup_ids.split(',') if sid.strip()])
    if subscribe_trustpilot_discovery_ids:
        event_ids_to_subscribe.extend([tid.strip() for tid in subscribe_trustpilot_discovery_ids.split(',') if tid.strip()])
    if subscribe_tripadvisor_discovery_ids:
        event_ids_to_subscribe.extend([tid.strip() for tid in subscribe_tripadvisor_discovery_ids.split(',') if tid.strip()])
    if subscribe_google_places_discovery_ids:
        event_ids_to_subscribe.extend([tid.strip() for tid in subscribe_google_places_discovery_ids.split(',') if tid.strip()])


    if not event_ids_to_subscribe:
        logger.warning("SSE Stream Endpoint: No task_ids, job_ids, or brand_events provided for subscription.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No event IDs provided for subscription.")

    # Generate unique client ID for logging and potential future direct messaging (though pub/sub is primary)
    client_connection_id = str(uuid.uuid4())
    logger.info(f"SSE client '{client_connection_id}' connecting. Subscribing to event_ids: {event_ids_to_subscribe}")

    async def event_publisher():
        logger.info(f"SSE Publisher (client: {client_connection_id}): Event publisher started for event_ids: {event_ids_to_subscribe}")
        
        pubsub = None # Initialize pubsub client
        try:
            pubsub = _redis_pool.pubsub()
            
            # Subscribe to each relevant Redis channel
            # Channel names are prefixed with "sse:" followed by the event_id
            redis_channels = [f"sse:{event_id}" for event_id in event_ids_to_subscribe]
            if redis_channels: # Ensure there are channels to subscribe to
                 await pubsub.subscribe(*redis_channels)
                 logger.info(f"SSE Publisher (client: {client_connection_id}): Subscribed to Redis channels: {redis_channels}")
            else:
                logger.warning(f"SSE Publisher (client: {client_connection_id}): No valid Redis channels to subscribe to based on input. Closing connection.")
                # Optionally send a specific SSE message about this before closing
                yield f"data: {json.dumps({'event_group': 'system', 'id': 'error', 'data': {'message': 'No valid channels to subscribe to.'}})}\n\n"
                return # Exit the publisher

            # Send an initial connection confirmation event
            initial_connection_event = {
                "event_group": "system", "id": "connection",
                "data": {"status": "connected", "client_id": client_connection_id, "subscribed_to": event_ids_to_subscribe, "message": "SSE connection established and subscribed to channels."}
            }
            yield f"data: {json.dumps(initial_connection_event)}\n\n"
            logger.info(f"SSE Publisher (client: {client_connection_id}): Sent initial connection event.")

            HEARTBEAT_INTERVAL_SECONDS = 15  # Send a heartbeat every 15 seconds
            last_heartbeat_time = time.monotonic()

            while True:
                if await request.is_disconnected():
                    logger.info(f"SSE client '{client_connection_id}' disconnected (detected by request.is_disconnected()).")
                    break
                
                try:
                    # Listen for messages from Redis Pub/Sub with a timeout
                    # The timeout allows checking for client disconnect and sending heartbeats
                    message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=1.1)
                    
                    if message and message.get("type") == "message":
                        event_data_str = message["data"]
                        logger.debug(f"SSE Publisher (client: {client_connection_id}): Received message from Redis channel '{message['channel']}': {event_data_str}")
                        # The message from Redis is already a JSON string of the full_event_payload
                        yield f"data: {event_data_str}\n\n"
                        last_heartbeat_time = time.monotonic() # Reset heartbeat timer on message
                        
                        # Optional: Check for terminal events within the message data if needed to close from server-side
                        try:
                            parsed_data = json.loads(event_data_str)
                            if parsed_data.get("data", {}).get("status") in ["completed", "failed", "timeout", "error_report_generation"]:
                                event_specific_id = parsed_data.get("id")
                                logger.info(f"SSE Publisher (client: {client_connection_id}): Detected terminal status '{parsed_data['data']['status']}' for event_id '{event_specific_id}'.")
                                # If subscribing to multiple, don't close connection on one task's completion.
                                # Client should handle individual task completions.
                                # If only one subscription, could consider closing here.
                        except json.JSONDecodeError:
                             logger.warning(f"SSE Publisher (client: {client_connection_id}): Could not parse JSON from Redis message data: {event_data_str}")
                        # --- NEW: Check for manual lookup terminal events ---
                        try:
                            parsed_data = json.loads(event_data_str)
                            # Check if the event is for manual lookup and if its status is terminal
                            if parsed_data.get("event_group") == "manual_lookup_discovery" and parsed_data.get("data", {}).get("status") in ["completed", "failed", "completed_empty"]:
                                event_specific_id = parsed_data.get("id")
                                logger.info(f"SSE Publisher (client: {client_connection_id}): Detected terminal status for manual lookup event_id '{event_specific_id}'.")
                        except json.JSONDecodeError:
                            logger.warning(f"SSE Publisher (client: {client_connection_id}): Could not parse JSON from Redis message data: {event_data_str}")
                        
                except asyncio.TimeoutError:
                    # No message from Redis within timeout, check for heartbeat
                    current_time = time.monotonic()
                    if current_time - last_heartbeat_time > HEARTBEAT_INTERVAL_SECONDS:
                        logger.debug(f"SSE Publisher (client: {client_connection_id}): Sending heartbeat.")
                        yield ":heartbeat\n\n" 
                        last_heartbeat_time = current_time
                    continue # Loop to check for disconnect or wait for next message/heartbeat
                
                except aioredis.RedisError as e:
                    logger.error(f"SSE Publisher (client: {client_connection_id}): Redis error while getting message: {e}", exc_info=True)
                    # Potentially break if Redis connection is lost
                    yield f"data: {json.dumps({'event_group': 'system', 'id': 'error', 'data': {'message': 'Redis connection error.'}})}\n\n"
                    await asyncio.sleep(5) # Wait a bit before trying to reconnect or break
                    # Consider attempting to re-subscribe if connection is flaky
                    # For now, we might break if Redis errors persist
                    # Re-ping to check connection.
                    if _redis_pool:
                        try:
                            await _redis_pool.ping()
                        except aioredis.RedisError:
                            logger.error(f"SSE Publisher (client: {client_connection_id}): Redis ping failed after error. Breaking from publisher loop.")
                            break # Break if Redis seems down
                    else: # if _redis_pool became None due to startup issues earlier
                        logger.error(f"SSE Publisher (client: {client_connection_id}): _redis_pool is None. Breaking.")
                        break


                except Exception as e: 
                    logger.error(f"SSE Publisher (client: {client_connection_id}): Unexpected error in publisher loop: {e}", exc_info=True)
                    # Depending on the error, might want to break or continue
                    # Sending a generic error to the client might be useful.
                    try:
                        yield f"data: {json.dumps({'event_group': 'system', 'id': 'error', 'data': {'message': f'Internal server error in SSE stream: {str(e)}'}})}\n\n"
                    except Exception: # Handle error during error reporting
                        pass
                    break # Break on unhandled errors to prevent tight loops

        except Exception as e:
            logger.error(f"SSE Publisher (client: {client_connection_id}): Error setting up Redis subscription or initial send: {e}", exc_info=True)
            try:
                yield f"data: {json.dumps({'event_group': 'system', 'id': 'error', 'data': {'message': f'Failed to initialize SSE stream: {str(e)}'}})}\n\n"
            except Exception:
                pass # If can't even send this, just log and clean up
        finally:
            logger.info(f"SSE Publisher (client: {client_connection_id}): Cleaning up event publisher.")
            if pubsub:
                try:
                    await pubsub.unsubscribe() # Unsubscribe from all channels
                    await pubsub.aclose() # Close the pubsub connection
                    logger.info(f"SSE Publisher (client: {client_connection_id}): Unsubscribed and closed Redis pubsub.")
                except Exception as e_pubsub_close:
                    logger.error(f"SSE Publisher (client: {client_connection_id}): Error during pubsub cleanup: {e_pubsub_close}", exc_info=True)
            logger.info(f"SSE Publisher (client: {client_connection_id}): Event publisher finished.")

    return StreamingResponse(event_publisher(), media_type="text/event-stream")

# Add Pydantic model for the chat request
class ArchetypeChatMessageRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)

# --- NEW ENDPOINT FOR ARCHETYPE CHAT ---
@app.post("/api/archetype-chat/{archetype_identifier}/message")
async def archetype_chat_send_message(
    archetype_identifier: str, # Can be ID or Name
    chat_request: ArchetypeChatMessageRequest,
    user_data = Depends(get_current_user)
):
    usuario_id = int(user_data["sub"])
    logger.info(f"Archetype chat message received for user {usuario_id}, archetype_identifier: {archetype_identifier}")

    # Fetch brand_name (synchronous, run in thread)
    brand_name = await asyncio.to_thread(get_marca_name_by_id, usuario_id)
    if not brand_name:
        logger.error(f"No brand found for user {usuario_id} for archetype chat.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No brand associated with this user found."
        )

    # Fetch archetype details (synchronous, run in thread)
    archetype_details = await asyncio.to_thread(fetch_single_archetype_details, brand_name, archetype_identifier)
    if not archetype_details:
        logger.error(f"Archetype '{archetype_identifier}' not found for brand '{brand_name}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archetype '{archetype_identifier}' not found for this brand."
        )

    # Construct the system prompt using various fields from archetype_details
    system_prompt_parts = [
        f"You are '{archetype_details.get('name', 'an archetype')}'.",
        f"Your general description is: {archetype_details.get('description', archetype_details.get('general_description', 'No general description available.'))}"
    ]
    # Add more details to the persona
    if archetype_details.get('values'):
        system_prompt_parts.append(f"Your core values include: {', '.join(archetype_details['values'])}.")
    if archetype_details.get('goals_and_objectives'):
        system_prompt_parts.append(f"Your main goals and objectives are: {', '.join(archetype_details['goals_and_objectives'])}.")
    if archetype_details.get('pain_points'):
        system_prompt_parts.append(f"You often experience these pain points: {', '.join(archetype_details['pain_points'])}.")
    if archetype_details.get('fears_and_concerns'):
        system_prompt_parts.append(f"Your fears and concerns include: {', '.join(archetype_details['fears_and_concerns'])}.")
    if archetype_details.get('social_behavior'):
        system_prompt_parts.append(f"Regarding your social behavior: {archetype_details['social_behavior']}.")
    if archetype_details.get('internal_narrative'):
        system_prompt_parts.append(f"Your internal narrative or deep motivations are: {archetype_details['internal_narrative']}.")


    system_prompt_parts.append(
        "Converse naturally based on this persona. "
        "IMPORTANT: Do NOT explicitly state your name or that you are an archetype or an AI. "
        "Simply embody the persona and respond to the user's messages from that perspective. Be helpful and engaging."
    )
    system_prompt = " ".join(system_prompt_parts)
    
    logger.debug(f"System prompt for LLM (Archetype Chat): {system_prompt}")

    # Prepare message history for LLM
    messages_for_llm = []
    if chat_request.history: # Ensure history is not None
        messages_for_llm.extend(chat_request.history)
    messages_for_llm.append({"role": "user", "content": chat_request.message})
    
    # Call LLM (synchronous function, run in thread)
    llm_response = await asyncio.to_thread(
        get_llm_chat_response,
        system_prompt,
        messages_for_llm
    )

    if isinstance(llm_response, dict) and "error" in llm_response:
        logger.error(f"LLM call failed for archetype chat (user {usuario_id}, archetype {archetype_identifier}): {llm_response['error']}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error communicating with the AI model: {llm_response['error']}"
        )
    
    if not isinstance(llm_response, str):
        logger.error(f"Unexpected LLM response type for archetype chat: {type(llm_response)}. Response: {llm_response}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Received an unexpected response format from the AI model."
        )

    logger.info(f"LLM response for archetype chat (user {usuario_id}, archetype {archetype_identifier}): {llm_response[:100]}...")
    return {"response": llm_response}

# --- Global stores for Bright Data Amazon Discovery (temporary) ---
# Key: snapshot_id from Bright Data
# Value: List of product dictionaries
amazon_brightdata_discovery_results: Dict[str, List[Dict]] = {}
# Key: snapshot_id
# Value: "triggered", "processing_webhook", "completed", "failed_trigger", "failed_webhook", "failed_download"
amazon_brightdata_discovery_status: Dict[str, str] = {}


# --- Pydantic Models for Bright Data ---
class AmazonBrightDataDiscoveryRequest(BaseModel):
    brand_name: str
    country: str
    
class BrightDataWebhookAuthHeader(BaseModel): # For dependency injection if needed, or manual check
    authorization: str

class BrightDataWebhookPayload(BaseModel):
    # Based on Bright Data documentation / assumptions
    # This will likely need to be adjusted once a real webhook payload is inspected
    event_type: Optional[str] = None # e.g., "snapshot.ready", "job.done"
    dataset_id: Optional[str] = None
    snapshot_id: str # This should be present
    status: Optional[str] = None # e.g., "ready", "failed"
    data: Optional[List[Dict]] = None # Direct data payload (if small enough)
    download_url: Optional[HttpUrl] = None # Link to download larger datasets
    records_count: Optional[int] = None
    # Potentially other fields from BrightData
    customer_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    collection_name: Optional[str] = None # If using 'Data Collector' type integrations

@app.post("/api/amazon/brightdata/discover-products")
async def trigger_amazon_product_discovery_via_brightdata(
    request_data: AmazonBrightDataDiscoveryRequest,
    user_data = Depends(get_current_user)
):
    global _arq_redis_pool
    if not _arq_redis_pool:
        logger.error("Cannot enqueue Amazon discovery. ARQ Redis pool is not available.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue service is currently unavailable."
        )

    usuario_id = int(user_data["sub"])
    brand_name = request_data.brand_name
    discovery_task_id = f"amazon_discovery_{uuid.uuid4()}"
    logger.info(f"User {usuario_id} enqueuing Bright Data Amazon discovery for brand: {brand_name} with task ID: {discovery_task_id}")

    try:
        await _arq_redis_pool.enqueue_job(
            'trigger_amazon_keyword_discovery_task',
            discovery_task_id,
            brand_name,
            request_data.country
        )
        logger.info(f"Enqueued 'trigger_amazon_keyword_discovery_task' with ID '{discovery_task_id}'.")
        return {
            "message": "Amazon product discovery process initiated.",
            "discovery_task_id": discovery_task_id
        }
    except Exception as e:
        logger.error(f"Error enqueuing 'trigger_amazon_keyword_discovery_task': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue Amazon discovery task.")

@app.post("/api/webhooks/brightdata/amazon-discovery-complete")
async def webhook_brightdata_amazon_discovery_complete(
    request: Request,
    discovery_task_id: Optional[str] = Query(None) # Added to capture from webhook URL
):
    raw_body = {} # Initialize raw_body to an empty dict
    try:
        raw_body = await request.json()
        logger.debug(f"Webhook raw body (parsed as JSON by FastAPI): {raw_body}")
    except json.JSONDecodeError:
        logger.warning("Webhook payload is not valid JSON. Snapshot_id must come from headers if this occurs and body is expected.")
    except Exception as e:
        logger.debug(f"Could not re-read/log raw body or body was not JSON: {e}")


    # 1. Determine the Snapshot ID
    snapshot_id = raw_body.get("snapshot_id") if isinstance(raw_body, dict) else None
    
    if not snapshot_id:
        snapshot_id = request.headers.get("X-Bd-Snapshot-Id") or request.headers.get("X-Snapshot-ID")
        if snapshot_id:
            logger.info(f"Found snapshot_id ('{snapshot_id}') in headers.")
    
    if not snapshot_id:
        logger.error("Webhook payload received, but snapshot_id is missing from JSON body or known headers. Cannot process.")
        raise HTTPException(status_code=400, detail="Snapshot ID missing in webhook request (not in body or headers).")
    
    # NEW: Get our internal task_id from Redis using the snapshot_id from Bright Data
    if not discovery_task_id and _redis_pool:
        try:
            discovery_task_id = await _redis_pool.get(f"snapshot_to_task:{snapshot_id}")
            if discovery_task_id:
                logger.info(f"Retrieved discovery_task_id '{discovery_task_id}' from Redis for snapshot '{snapshot_id}'.")
            else:
                 logger.warning(f"Could not find a discovery_task_id in Redis for snapshot '{snapshot_id}'. SSE events might not be sent.")
        except Exception as e:
            logger.error(f"Error retrieving task_id from Redis for snapshot {snapshot_id}: {e}")

    if not discovery_task_id:
        logger.error(f"Cannot process webhook for snapshot {snapshot_id} without a discovery_task_id.")
        # We don't raise HTTPException here to avoid BrightData retrying a non-recoverable error.
        return JSONResponse(content={"message": "Webhook ignored, no associated task found."}, status_code=200)

    # 2. Verify Webhook Secret
    expected_webhook_secret = os.getenv("BRIGHTDATA_WEBHOOK_SECRET")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not expected_webhook_secret:
        logger.warning(f"Webhook (snapshot: {snapshot_id}) security misconfiguration or missing auth header.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook authentication failed (config).")

    if auth_header != f"Bearer {expected_webhook_secret}":
        logger.warning(f"Invalid webhook (snapshot: {snapshot_id}) Authorization token received: {auth_header}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook authentication failed (token).")

    logger.info(f"Webhook authenticated successfully for snapshot_id: {snapshot_id} (Task ID: {discovery_task_id})")

    products_list = get_snapshot_results(snapshot_id)

    final_status_for_sse: str
    message_for_sse: str
    record_count_for_sse: int

    if products_list is not None:
        logger.info(f"Applying user-defined filter to {len(products_list)} products from keyword discovery.")
        filtered_products = []
        for product in products_list:
            original_keyword = product.get("search_keyword") or product.get("keyword")

            if not original_keyword:
                logger.warning(f"Product result missing 'search_keyword' or 'keyword'. Including it without filtering. Product: {product.get('name')}")
                filtered_products.append(product)
                continue

            product_name = (product.get("name") or "").lower()
            product_url_path = (product.get("url") or "").split('?')[0].lower()
            product_brand = (product.get("brand") or "").lower()
            keyword_lower = str(original_keyword).lower()

            if keyword_lower == product_brand or keyword_lower in product_name or keyword_lower in product_url_path:
                product['title'] = product.get('name', 'Unnamed Product')
                filtered_products.append(product)
            else:
                logger.info(f"Filtering out product '{product.get('name')}' because keyword '{original_keyword}' was not in brand, name, or url path.")

        products_list = filtered_products
        logger.info(f"Found {len(products_list)} products after filtering.")

        # Save to DB instead of global dict
        # This part requires a DB utility function, let's assume one exists or can be added.
        # For now, we'll just dispatch the results via SSE.

        final_status_for_sse = "completed"
        message_for_sse = f"Product discovery completed. {len(products_list)} products found."
        record_count_for_sse = len(products_list)
    else:
        # get_snapshot_results failed
        final_status_for_sse = "failed"
        message_for_sse = f"Failed to retrieve/process product data for snapshot {snapshot_id} from Bright Data."
        record_count_for_sse = 0

    sse_payload_data = {
        "status": final_status_for_sse,
        "snapshot_id": snapshot_id,
        "task_id": discovery_task_id, # Include our internal task id
        "message": message_for_sse,
        "record_count": record_count_for_sse,
        "products": products_list if final_status_for_sse == "completed" else [] # Send products in the final event
    }

    if final_status_for_sse != "completed":
        sse_payload_data["error_detail"] = f"Snapshot {snapshot_id} processing resulted in status: {final_status_for_sse}."

    try:
        # The event_id for dispatching is our internal discovery_task_id
        await sse_dispatch_event(
            redis_pool=_redis_pool,  # Add this line
            event_id=discovery_task_id,
            event_group="amazon_discovery_update",
            data=sse_payload_data
        )
        logger.info(f"Dispatched SSE event for task {discovery_task_id} from webhook. Status: {final_status_for_sse}")
    except Exception as e:
        logger.error(f"Failed to dispatch SSE event for task {discovery_task_id} from webhook: {e}", exc_info=True)
    
    # Clean up the Redis mapping
    if _redis_pool:
        await _redis_pool.delete(f"snapshot_to_task:{snapshot_id}")

    return JSONResponse(content={"message": f"Webhook processed. Status: {final_status_for_sse}"}, status_code=200)

@app.get("/api/amazon/brightdata/products/{snapshot_id}")
async def get_amazon_brightdata_discovered_products(
    snapshot_id: str,
    user_data = Depends(get_current_user)
):
    # This endpoint is deprecated as results are now sent via SSE and saved to the DB.
    # It can be removed once the frontend is fully updated.
    # For now, return an empty response to avoid breaking old clients.
    logger.warning(f"Deprecated endpoint /api/amazon/brightdata/products/{snapshot_id} was called.")
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="This endpoint is deprecated. Product discovery results are now delivered via Server-Sent Events.")

# --- Global stores for Manual Product Lookup (temporary) ---
# Key: snapshot_id from Bright Data
# Value: List of product dictionaries
manual_lookup_results: Dict[str, List[Dict]] = {}
# Key: snapshot_id
# Value: "triggered", "processing_webhook", "completed", "failed"
manual_lookup_status: Dict[str, str] = {}


# --- Pydantic Models for Bright Data ---
class AmazonBrightDataDiscoveryRequest(BaseModel):
    brand_name: str
    
class ManualProductLookupRequest(BaseModel):
    identifiers: List[str]
    country: str 

class BrightDataWebhookAuthHeader(BaseModel): # For dependency injection if needed, or manual check
    authorization: str

class BrightDataWebhookPayload(BaseModel):
    # Based on Bright Data documentation / assumptions
    # This will likely need to be adjusted once a real webhook payload is inspected
    event_type: Optional[str] = None # e.g., "snapshot.ready", "job.done"
    dataset_id: Optional[str] = None
    snapshot_id: str # This should be present
    status: Optional[str] = None # e.g., "ready", "failed"
    data: Optional[List[Dict]] = None # Direct data payload (if small enough)
    download_url: Optional[HttpUrl] = None # Link to download larger datasets
    records_count: Optional[int] = None
    # Potentially other fields from BrightData
    customer_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    collection_name: Optional[str] = None # If using 'Data Collector' type integrations

@app.post("/api/products/manual-lookup/trigger")
async def trigger_manual_product_lookup_endpoint(
    request_data: ManualProductLookupRequest,
    user_data = Depends(get_current_user)
):
    """
    Triggers a manual product lookup for a list of identifiers using Bright Data.
    """
    global _arq_redis_pool
    if not _arq_redis_pool:
        raise HTTPException(status_code=503, detail="Worker queue not available.")

    user_id = user_data.get("sub")
    task_id = f"manual_lookup_{uuid.uuid4()}"

    logger.info(f"User {user_id} enqueuing manual product lookup (Task ID: {task_id}) for {len(request_data.identifiers)} items in country '{request_data.country}'.")

    try:
        await _arq_redis_pool.enqueue_job(
            'trigger_manual_product_lookup_task',
            task_id,
            request_data.identifiers,
            request_data.country,
            str(user_id)
        )

        return {"message": "Manual product lookup process initiated.", "task_id": task_id}

    except Exception as e:
        logger.error(f"Failed to enqueue manual product lookup (Task ID: {task_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate manual product lookup: {e}")


@app.post("/api/webhooks/brightdata/amazon-reviews-complete")
async def webhook_brightdata_amazon_reviews_complete(request: Request):
    """
    Receives a webhook from Bright Data and enqueues a background task to process the Amazon reviews.
    This keeps the endpoint lightweight and responsive.
    """
    global _arq_redis_pool
    logger.info("Received Bright Data Amazon reviews complete webhook, queuing for worker processing.")

    # 1. Authenticate Webhook
    auth_header = request.headers.get("Authorization")
    WEBHOOK_SECRET = os.getenv("BRIGHTDATA_WEBHOOK_SECRET")
    if not auth_header or auth_header != f"Bearer {WEBHOOK_SECRET}":
        logger.warning("Unauthorized webhook access attempt for amazon-reviews-complete")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # 2. Parse payload to get snapshot_id
    try:
        payload_data = await request.json()
        snapshot_id = payload_data.get("snapshot_id")
        if not snapshot_id:
            raise ValueError("snapshot_id missing from payload")
        logger.info(f"Webhook for snapshot_id: {snapshot_id} received.")
    except (ValueError, json.JSONDecodeError) as e:
        raw_body = await request.body()
        logger.error(f"Failed to parse Bright Data webhook payload: {e}. Raw body: {raw_body.decode()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or incomplete payload")

    # 3. Check if ARQ pool is available
    if not _arq_redis_pool:
        logger.error(f"Cannot process webhook for snapshot {snapshot_id}. ARQ Redis pool is not available.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Task queue service is currently unavailable.")

    # 4. Enqueue the processing task
    try:
        await _arq_redis_pool.enqueue_job(
            'process_amazon_reviews_webhook_task',
            snapshot_id,
            payload_data
        )
        logger.info(f"Enqueued 'process_amazon_reviews_webhook_task' for snapshot_id: {snapshot_id}")
        return JSONResponse(content={"message": "Webhook received and queued for processing."}, status_code=202) # Accepted
    except Exception as e:
        logger.error(f"Error enqueuing 'process_amazon_reviews_webhook_task' for snapshot {snapshot_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue webhook processing task.")

@app.post("/api/webhooks/brightdata/manual-lookup-complete")
async def webhook_manual_lookup_complete(
    request: Request,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Webhook called by Bright Data when a manual product lookup job is complete.
    It retrieves the results, saves them, and notifies the user via SSE.
    """
    payload_bytes = await request.body()
    try:
        # It seems BrightData might send 'x-bd-data' header with URL instead of in payload sometimes
        # For now, we assume standard payload or must check headers. Let's stick to payload.
        webhook_payload = json.loads(payload_bytes)
        snapshot_id = webhook_payload.get("snapshot_id")
        logger.info(f"Received manual lookup webhook for snapshot_id: {snapshot_id}")
    except json.JSONDecodeError:
        logger.error("Failed to decode webhook payload JSON.")
        return JSONResponse(content={"message": "Invalid JSON"}, status_code=400)

    if not snapshot_id:
        return JSONResponse(content={"message": "snapshot_id missing from webhook payload"}, status_code=400)

    task_id = await _redis_pool.get(f"snapshot_to_task:{snapshot_id}")
    if not task_id:
        logger.warning(f"Could not find a task_id for snapshot_id {snapshot_id}. The task may have expired or was not set.")
        # Even if we can't find the task_id, we could still process the data, but we can't notify the user.
        # For now, we'll stop here.
        return JSONResponse(content={"message": "No associated task found for this snapshot."}, status_code=404)

    job_data_key = f"manual_lookup_job:{task_id}"
    job_data = await _redis_pool.hgetall(job_data_key)
    user_id = job_data.get("user_id")
    brand_name = job_data.get("brand_name")
    
    if not user_id or not brand_name:
        logger.error(f"Missing user_id or brand_name in Redis for task {task_id}")
        # Clean up and exit
        await _redis_pool.delete(f"snapshot_to_task:{snapshot_id}")
        await _redis_pool.delete(job_data_key)
        return JSONResponse(content={"message": "Job metadata missing."}, status_code=500)

    # Now, get the actual product data using the snapshot_id
    products = get_snapshot_results(snapshot_id)
    saved_count = 0

    if products is not None:
        logger.info(f"Successfully retrieved {len(products)} products for snapshot {snapshot_id}. Saving to DB.")
        for product in products:
            if 'identifier' not in product and 'asin' in product:
                product['identifier'] = product['asin']
            try:
                await save_discovered_product_in_db(db, product, brand_name, user_id)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving product {product.get('identifier')} for brand {brand_name}: {e}", exc_info=True)

        logger.info(f"Saved {saved_count}/{len(products)} products to the database for brand '{brand_name}'.")
        status, msg = ("completed", f"Successfully found and saved {saved_count} products.") if products else ("completed_empty", "Lookup completed, but no products were found.")
    else:
        logger.error(f"Failed to retrieve results for manual lookup snapshot {snapshot_id}.")
        status, msg = "failed", "Failed to retrieve product data from provider."
    
    await sse_dispatch_event(
        redis_pool=_redis_pool,
        event_id=task_id,
        event_group="manual_lookup_discovery",
        data={"status": status, "task_id": task_id, "message": msg, "products": products or []}
    )

    await _redis_pool.delete(f"snapshot_to_task:{snapshot_id}")
    await _redis_pool.delete(job_data_key)
    logger.info(f"Cleaned up Redis keys for manual lookup job: {task_id}")
    
    return JSONResponse(content={"message": "Webhook processed."}, status_code=200)

class TrustpilotDiscoveryRequest(BaseModel):
    brand_name: str
    country: str
    limit: int = 5
    url: Optional[str] = None
    

class DiscoveredProductPayload(BaseModel):
    identifier: str
    title: Optional[str] = None
    url: Optional[str] = None
    asin: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    brand: Optional[str] = None
    final_price: Optional[Union[str, float, int]] = None
    currency: Optional[str] = None
    scrapeTargets: Optional[Dict[str, bool]] = None
    
    class Config:
        extra = "allow"

class DiscoveredProductIdentifier(BaseModel):
    identifier: str

@app.post("/api/products/discovered-item", status_code=status.HTTP_201_CREATED)
async def save_discovered_product_item(
    product_payload: DiscoveredProductPayload,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    
    user_id = user_data.get("sub")
    brand_name = get_marca_name_by_id(user_id)
    if not brand_name or not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User brand information is missing."
        )

    try:
        product_dict = product_payload.model_dump()
        document_id = await save_discovered_product_in_db(
            db=db,
            product=product_dict,
            brand_name=brand_name,
            user_id=user_id
        )
        return {"message": "Product saved successfully", "id": str(document_id)}
    except Exception as e:
        logger.error(f"Error saving discovered product for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the product."
        )

@app.delete("/api/products/discovered-item", status_code=status.HTTP_204_NO_CONTENT)
async def remove_discovered_product_item(
    identifier_request: DiscoveredProductIdentifier,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    user_id = user_data.get("sub")
    brand_name = get_marca_name_by_id(user_id)
    if not brand_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User brand information is missing."
        )
    
    try:
        deleted_count = await delete_discovered_product_from_db(
            db=db,
            identifier=identifier_request.identifier,
            brand_name=brand_name
        )
        if deleted_count == 0:
            logger.warning(f"Attempted to delete product with identifier '{identifier_request.identifier}' for brand '{brand_name}', but it was not found.")
        return
    except Exception as e:
        logger.error(f"Error deleting discovered product for brand {brand_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the product."
        )

@app.get("/api/products/discovered-items", response_model=List[Dict])
async def get_saved_discovered_products(
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Fetches all previously saved ("discovered") products for the user's brand.
    """
    user_id = user_data.get("sub")
    brand_name = get_marca_name_by_id(user_id)
    if not brand_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User brand information is missing."
        )

    # Local import to avoid circular dependency issues at module level
    from helper.utilsdb import fetch_discovered_products
    
    try:
        products = await fetch_discovered_products(db, brand_name)
        return products
    except Exception as e:
        logger.error(f"Error fetching discovered products for brand {brand_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching saved products."
        )

async def _run_trustpilot_discovery(task_id: str, brand_name: str, country: str):
    """
    Background task to run Trustpilot URL discovery and dispatch SSE events.
    """
    global _redis_pool
    await asyncio.sleep(2.0)  # Give frontend time to connect to SSE stream
    try:
        logger.info(f"Task [{task_id}] - Starting Trustpilot URL discovery for '{brand_name}' in country '{country}'.")
        await sse_dispatch_event(
            _redis_pool,
            event_id=task_id,
            event_group="trustpilot_discovery",
            data={"status": "started", "message": f"Starting Trustpilot URL discovery for '{brand_name}'."}
        )
        
        urls = await gather_trustpilot_urls(brand_name, country)

        logger.info(f"Task [{task_id}] - Discovery finished. Found {len(urls)} URLs.")
        await sse_dispatch_event(
            _redis_pool,
            event_id=task_id,
            event_group="trustpilot_discovery",
            data={"status": "completed", "urls": urls, "message": "Discovery complete."}
        )
    except Exception as e:
        logger.error(f"Task [{task_id}] - Error during Trustpilot URL discovery: {e}", exc_info=True)
        await sse_dispatch_event(
            _redis_pool,
            event_id=task_id,
            event_group="trustpilot_discovery",
            data={"status": "failed", "error": str(e), "message": "An error occurred during discovery."}
        )

@app.post("/api/trustpilot/discover")
async def discover_truspilot_pages(
    request: TrustpilotDiscoveryRequest,
    background_tasks: BackgroundTasks,
    user_data = Depends(get_current_user)
):
    user_id = int(user_data["sub"])
    user_brand_name = get_marca_name_by_id(user_id)
    if not user_brand_name or not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User brand information is missing."
        )

    data = request.model_dump()
    brand_name_to_search = data.get("brand_name")
    country = data.get("country")
    url = data.get("url")

    if url:
        return {"urls": [url.split('?')[0]]}

    if not brand_name_to_search:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A brand name is required for discovery."
        )

    task_id = str(uuid.uuid4())
    logger.info(f"Task [{task_id}] - Scheduling Trustpilot URL discovery for brand '{brand_name_to_search}'")

    background_tasks.add_task(
        _run_trustpilot_discovery,
        task_id=task_id,
        brand_name=brand_name_to_search,
        country=country,
    )

    return {"message": "Trustpilot URL discovery initiated.", "discovery_task_id": task_id}
    
class TripadvisorDiscoveryRequest(BaseModel):
    brand_name: str
    country: str
    url: Optional[str] = None

@app.post("/api/tripadvisor/discover")
async def discover_tripadvisor_pages(
    request: TripadvisorDiscoveryRequest,
    background_tasks: BackgroundTasks,
    user_data = Depends(get_current_user)
):
    user_id = int(user_data["sub"])
    user_brand_name = get_marca_name_by_id(user_id)
    if not user_brand_name or not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User brand information is missing."
        )

    data = request.model_dump()
    brand_name_to_search = data.get("brand_name")
    country = data.get("country")
    url = data.get("url")

    if url:
        return {"urls": [url.split('?')[0]]}

    if not brand_name_to_search:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A brand name is required for discovery."
        )

    task_id = str(uuid.uuid4())
    logger.info(f"Task [{task_id}] - Scheduling TripAdvisor URL discovery for brand '{brand_name_to_search}'")

    background_tasks.add_task(
        _run_tripadvisor_discovery,
        task_id=task_id,
        brand_name=brand_name_to_search,
        country=country,
    )

    return {"message": "TripAdvisor URL discovery initiated.", "discovery_task_id": task_id}


async def _run_tripadvisor_discovery(task_id: str, brand_name: str, country: str):
    """
    Background task to run TripAdvisor URL discovery and dispatch SSE events.
    """
    global _redis_pool
    await asyncio.sleep(2.0)  # Give frontend time to connect to SSE stream
    try:
        logger.info(f"Task [{task_id}] - Starting TripAdvisor URL discovery for '{brand_name}' in country '{country}'.")
        await sse_dispatch_event(
            _redis_pool,
            event_id=task_id,
            event_group="tripadvisor_discovery",
            data={"status": "started", "message": f"Starting TripAdvisor URL discovery for '{brand_name}'."}
        )
        
        urls = await gather_tripadvisor_urls(brand_name, country)

        logger.info(f"Task [{task_id}] - TripAdvisor discovery finished. Found {len(urls)} URLs.")
        await sse_dispatch_event(
            _redis_pool,
            event_id=task_id,
            event_group="tripadvisor_discovery",
            data={"status": "completed", "urls": urls, "message": "Discovery complete."}
        )
    except Exception as e:
        logger.error(f"Task [{task_id}] - Error during TripAdvisor URL discovery: {e}", exc_info=True)
        await sse_dispatch_event(
            _redis_pool,
            event_id=task_id,
            event_group="tripadvisor_discovery",
            data={"status": "failed", "error": str(e), "message": "An error occurred during discovery."}
        )

# <<< Competitor Management Endpoints >>>

@app.post("/api/competitors", response_model=Competitor, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    competitor_create: CompetitorCreate,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Creates a new competitor for the current user.
    """
    user_id = int(user_data["sub"])
    competitor_name = competitor_create.name

    # Check if competitor with the same name already exists for this user
    existing_competitor = await db.competitors.find_one(
        {"user_id": user_id, "competitors.name": competitor_name}
    )
    if existing_competitor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A competitor with the name '{competitor_name}' already exists."
        )

    new_competitor = Competitor(name=competitor_name)

    await db.competitors.update_one(
        {"user_id": user_id},
        {"$push": {"competitors": new_competitor.dict()}},
        upsert=True
    )
    return new_competitor

@app.get("/api/competitors", response_model=List[Competitor])
async def get_competitors(
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves all competitors for the current user.
    """
    user_id = int(user_data["sub"])
    user_competitors_doc = await db.competitors.find_one({"user_id": user_id})
    if user_competitors_doc and "competitors" in user_competitors_doc:
        return user_competitors_doc["competitors"]
    return []

@app.get("/api/competitors/{competitor_id}", response_model=Competitor)
async def get_competitor(
    competitor_id: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves a single competitor by its ID.
    """
    user_id = int(user_data["sub"])
    user_competitors_doc = await db.competitors.find_one(
        {"user_id": user_id, "competitors.id": competitor_id},
        {"competitors.$": 1}
    )
    if user_competitors_doc and user_competitors_doc.get("competitors"):
        return user_competitors_doc["competitors"][0]
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")

@app.put("/api/competitors/{competitor_id}", response_model=Competitor)
async def update_competitor(
    competitor_id: str,
    competitor_update: CompetitorUpdate,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Updates a competitor's details (e.g., name).
    """
    user_id = int(user_data["sub"])
    update_fields = competitor_update.dict(exclude_unset=True)

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    # Construct the update object for fields within the competitors array element
    update_doc = {f"competitors.$.{key}": value for key, value in update_fields.items()}

    result = await db.competitors.update_one(
        {"user_id": user_id, "competitors.id": competitor_id},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")

    # Fetch and return the updated competitor
    updated_competitor = await get_competitor(competitor_id, user_data, db)
    return updated_competitor

@app.delete("/api/competitors/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Deletes a competitor.
    """
    user_id = int(user_data["sub"])
    result = await db.competitors.update_one(
        {"user_id": user_id},
        {"$pull": {"competitors": {"id": competitor_id}}}
    )

    if result.modified_count == 0:
        # This could mean the user document exists but the competitor was not found
        # Or the user has no competitors doc at all. Either way, it's a 404 for the competitor.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found to delete")


# <<< Competitor Source Management Endpoints >>>

@app.post("/api/competitors/{competitor_id}/sources", response_model=CompetitorSourceConfig, status_code=status.HTTP_201_CREATED)
async def add_competitor_source(
    competitor_id: str,
    source_config: CompetitorSourceConfig,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Adds a new source configuration to a specific competitor.
    """
    user_id = int(user_data["sub"])
    
    # First, ensure the competitor exists and get its current sources
    competitor = await get_competitor(competitor_id, user_data, db)
    
    # Check if a source of the same type already exists
    if any(s['source_type'] == source_config.source_type for s in competitor['sources']):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Source type '{source_config.source_type}' already configured for this competitor. Use PUT to update."
        )

    await db.competitors.update_one(
        {"user_id": user_id, "competitors.id": competitor_id},
        {"$push": {"competitors.$.sources": source_config.model_dump()}}
    )
    return source_config

@app.get("/api/competitors/{competitor_id}/sources", response_model=List[CompetitorSourceConfig])
async def get_competitor_sources(
    competitor_id: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves all source configurations for a specific competitor.
    """
    competitor = await get_competitor(competitor_id, user_data, db)
    return competitor.get("sources", [])

@app.put("/api/competitors/{competitor_id}/sources/{source_type}", response_model=CompetitorSourceConfig)
async def update_competitor_source(
    competitor_id: str,
    source_type: str,
    source_config: CompetitorSourceConfig,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Updates a specific source configuration for a competitor.
    """
    user_id = int(user_data["sub"])
    if source_type != source_config.source_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source type in path does not match body.")

    # We need to pull the old source and push the new one.
    # This is more robust than trying to $set nested fields.
    pull_result = await db.competitors.update_one(
        {"user_id": user_id, "competitors.id": competitor_id},
        {"$pull": {"competitors.$.sources": {"source_type": source_type}}}
    )

    if pull_result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source configuration not found for this competitor.")

    push_result = await db.competitors.update_one(
        {"user_id": user_id, "competitors.id": competitor_id},
        {"$push": {"competitors.$.sources": source_config.dict()}}
    )
    
    return source_config

@app.delete("/api/competitors/{competitor_id}/sources/{source_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor_source(
    competitor_id: str,
    source_type: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Deletes a source configuration from a competitor.
    """
    user_id = int(user_data["sub"])
    result = await db.competitors.update_one(
        {"user_id": user_id, "competitors.id": competitor_id},
        {"$pull": {"competitors.$.sources": {"source_type": source_type}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source configuration not found to delete.")


# <<< Competitor Scraping Endpoint >>>

@app.post("/api/competitors/{competitor_id}/scrape", status_code=status.HTTP_202_ACCEPTED)
async def scrape_competitor_sources(
    competitor_id: str,
    background_tasks: BackgroundTasks,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Initiates a scraping job for all configured sources of a specific competitor.
    """
    user_id = int(user_data["sub"])
    
    # Get competitor details, which includes the sources
    competitor = await get_competitor(competitor_id, user_data, db)
    competitor_name = competitor['name']
    competitor_sources = competitor.get('sources', [])
    logger.info(f"Competitor sources: {competitor_sources}")

    if not competitor_sources:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No sources configured for this competitor to scrape.")

    # The scraping orchestration expects a list of SourceData objects.
    # We can use our CompetitorSourceConfig as it has a compatible structure.
    active_sources_data = [SourceData(**source) for source in competitor_sources]
    
    job_id = f"job_{uuid.uuid4().hex}"
    save_job(job_id, user_id)
    
    # Use the competitor's name as the brand_name for the scraping job
    background_tasks.add_task(
        _run_scraping_orchestration,
        job_id,
        active_sources_data,
        user_id,
        competitor_name,  # Key change: Pass competitor name as brand_name
        db
    )
    
    return {"job_id": job_id, "message": f"Scraping job initiated for competitor '{competitor_name}'."}

# <<< End of Competitor Feature Endpoints >>>
 
# --- Source Container Endpoints ---

class SourceContainer(BaseModel):
    id: str = Field(default_factory=lambda: f"sc_{uuid.uuid4().hex[:12]}")
    name: str
    sources: List[CompetitorSourceConfig] = Field(default_factory=list)

class SourceContainerCreate(BaseModel):
    name: str

class SourceContainerUpdate(BaseModel):
    name: Optional[str] = None


@app.post("/api/source-containers", response_model=SourceContainer, status_code=status.HTTP_201_CREATED)
async def create_source_container(
    source_container_create: SourceContainerCreate,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Creates a new source container for the user.
    """
    source_container = SourceContainer(name=source_container_create.name)
    container_doc = source_container.model_dump()
    container_doc["usuario_id"] = user_data["sub"]

    # Use the generated 'id' as the '_id' in MongoDB to ensure uniqueness and control.
    container_doc["_id"] = container_doc["id"]

    await db.source_containers.insert_one(container_doc)
    
    # Return the created object
    return source_container

@app.get("/api/source-containers", response_model=List[SourceContainer])
async def get_source_containers(
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves all source containers for the current user.
    """
    containers = await db.source_containers.find({"usuario_id": user_data["sub"]}).to_list(length=100)
    return containers

@app.get("/api/source-containers/{container_id}", response_model=SourceContainer)
async def get_source_container(
    container_id: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves a single source container by its ID.
    """
    container = await db.source_containers.find_one({"id": container_id, "usuario_id": user_data["sub"]})
    if not container:
        raise HTTPException(status_code=404, detail="Source container not found")
    return container

@app.put("/api/source-containers/{container_id}", response_model=SourceContainer)
async def update_source_container(
    container_id: str,
    container_update: SourceContainerUpdate,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Updates a source container's properties (e.g., name).
    """
    update_data = container_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    result = await db.source_containers.update_one(
        {"id": container_id, "usuario_id": user_data["sub"]},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source container not found")
    
    updated_container = await db.source_containers.find_one({"id": container_id, "usuario_id": user_data["sub"]})
    if not updated_container:
         raise HTTPException(status_code=404, detail="Source container not found after update")
    return updated_container

@app.delete("/api/source-containers/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source_container(
    container_id: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Deletes a source container.
    """
    result = await db.source_containers.delete_one({"id": container_id, "usuario_id": user_data["sub"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source container not found")
    return

@app.post("/api/source-containers/{container_id}/sources", response_model=CompetitorSourceConfig, status_code=status.HTTP_201_CREATED)
async def add_source_to_container(
    container_id: str,
    source_config: CompetitorSourceConfig,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Adds a new source configuration to a specific source container.
    """
    container = await db.source_containers.find_one({"id": container_id, "usuario_id": user_data["sub"]})
    if not container:
        raise HTTPException(status_code=404, detail="Source container not found")

    if any(s['source_type'] == source_config.source_type for s in container.get('sources', [])):
        raise HTTPException(status_code=400, detail=f"Source type '{source_config.source_type}' already exists in this container.")
    
    await db.source_containers.update_one(
        {"id": container_id, "usuario_id": user_data["sub"]},
        {"$push": {"sources": source_config.dict()}}
    )
    return source_config

@app.get("/api/source-containers/{container_id}/sources", response_model=List[CompetitorSourceConfig])
async def get_sources_for_container(
    container_id: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retrieves all source configurations for a specific source container.
    """
    container = await db.source_containers.find_one({"id": container_id, "usuario_id": user_data["sub"]})
    if not container:
        raise HTTPException(status_code=404, detail="Source container not found")
    return container.get("sources", [])

@app.put("/api/source-containers/{container_id}/sources/{source_type}", response_model=CompetitorSourceConfig)
async def update_source_in_container(
    container_id: str,
    source_type: str,
    source_config: CompetitorSourceConfig,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Updates an existing source configuration within a source container.
    """
    if source_type != source_config.source_type:
        raise HTTPException(status_code=400, detail="Source type in path does not match source type in body.")

    result = await db.source_containers.update_one(
        {"id": container_id, "usuario_id": user_data["sub"], "sources.source_type": source_type},
        {"$set": {"sources.$": source_config.dict()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source container or source type not found")
    
    return source_config

@app.delete("/api/source-containers/{container_id}/sources/{source_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source_from_container(
    container_id: str,
    source_type: str,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Deletes a source configuration from a source container.
    """
    result = await db.source_containers.update_one(
        {"id": container_id, "usuario_id": user_data["sub"]},
        {"$pull": {"sources": {"source_type": source_type}}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source container not found")
    if result.modified_count == 0:
        # This means the container was found, but the source_type wasn't in its array.
        # This isn't necessarily an error, but we can raise for strictness.
        raise HTTPException(status_code=404, detail="Source type not found in container")
    return

@app.post("/api/source-containers/{container_id}/scrape", status_code=status.HTTP_202_ACCEPTED)
async def scrape_container_sources(
    container_id: str,
    background_tasks: BackgroundTasks,
    user_data: dict = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Triggers the scraping process for all configured sources in a container.
    """
    container = await db.source_containers.find_one({"id": container_id, "usuario_id": user_data["sub"]})
    if not container:
        raise HTTPException(status_code=404, detail="Source container not found")

    active_sources_data = container.get("sources", [])
    if not active_sources_data:
        raise HTTPException(status_code=400, detail="No sources configured for this container.")

    # Get user brand name from their profile
    user_id = int(user_data["sub"])
    brand_name = get_marca_name_by_id(user_id)
    logger.info(f"Brand name: {brand_name}")
    
    # Generate job_id
    job_id = f"job_sc_{container_id}_{uuid.uuid4().hex[:12]}"
    
    # Save the job to the database
    save_job(job_id, user_data["sub"])

    # Create SourceData objects for orchestration
    source_data_list = [SourceData(**item) for item in active_sources_data]
    
    # Run the scraping orchestration in the background
    background_tasks.add_task(
        _run_scraping_orchestration, job_id, source_data_list, user_data["sub"], brand_name, db
    )
    
    return {"message": "Source container scraping process initiated.", "job_id": job_id}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)