import os
import jwt
import uuid
import hashlib
import datetime
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel, EmailStr, field_validator
from fastapi import Depends, HTTPException, status, Header
from dotenv import load_dotenv
import asyncio
import random
import string
import smtplib
from email.message import EmailMessage
import re
import logging

logger = logging.getLogger(__name__)
# Cargar variables de entorno
load_dotenv()

# Configuración de JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insightssecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

# Configuración de MySQL
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "tama")
}

# --- NUEVAS CONFIGURACIONES SMTP --- (Cargadas desde .env)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
# -----------------------------------

# Modelos de datos para autenticación
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    id: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class AdminLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    marca_id: int
    is_admin: Optional[bool] = False
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, password: str) -> str:
        # Validate minimum length
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        
        # Validate uppercase
        if not re.search(r'[A-Z]', password):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        
        # Validate lowercase
        if not re.search(r'[a-z]', password):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        
        # Validate special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("La contraseña debe contener al menos un carácter especial")
            
        return password

class AdminRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class MarcaCreate(BaseModel):
    name: str
    description: Optional[str] = None

# --- NUEVO MODELO Pydantic para verificar 2FA ---
class TwoFactorVerifyRequest(BaseModel):
    user_id: int
    code: str
# ---------------------------------------------

# Funciones de base de datos
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión a la base de datos"
        )

# Funciones de autenticación
def hash_password(password: str) -> str:
    """Genera un hash seguro para la contraseña"""
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

def check_password(hashed_password: str, user_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado"""
    try:
        # Intentar verificar como hash:salt
        password_part, salt_part = hashed_password.split(':')
        
        # Recalcular hash con el salt recuperado y la contraseña introducida
        recalculated_hash = hashlib.sha256(salt_part.encode() + user_password.encode()).hexdigest()
        
        # Comparación
        comparison_result = (password_part == recalculated_hash)
        
        return comparison_result
    except ValueError:
        # Si no tiene el formato correcto, comparar directamente (para desarrollo)
        return hashed_password == user_password
    except Exception as e:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verifica un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """Obtiene el usuario actual a partir del token de autorización"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if payload.get("role") != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para acceder a este recurso",
        )
    
    return payload

def get_current_admin(authorization: str = Header(None)) -> Dict[str, Any]:
    """Obtiene el administrador actual a partir del token de autorización"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de administrador",
        )
    
    return payload

# --- NUEVA FUNCIÓN --- 
def get_current_admin_or_corporate(authorization: str = Header(None)) -> Dict[str, Any]:
    """Obtiene el administrador (normal o corporativo) actual a partir del token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    allowed_roles = ["admin", "corporate_admin"]
    if payload.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de administrador para este recurso",
        )
    
    # Devolver el payload completo, que incluye el rol y el ID (sub)
    return payload
# --- FIN NUEVA FUNCIÓN ---

# Funciones para usuarios
async def authenticate_user(email: str, password: str) -> Tuple[bool, Dict[str, Any]]:
    """Autentica un usuario de forma asíncrona, ejecutando el código síncrono en un hilo."""
    
    def _sync_authenticate():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT u.*, m.name as marca_name FROM usuarios u "
                "JOIN marcas m ON u.marca_id = m.id "
                "WHERE u.email = %s AND u.is_active = TRUE",
                (email,)
            )
            user = cursor.fetchone()
            
            if not user or not check_password(user["password"], password):
                return False, {}
            
            # Eliminar la contraseña antes de devolver los datos
            user.pop("password", None)
            return True, user
        finally:
            if cursor:
                 cursor.close()
            if conn and conn.is_connected():
                 conn.close()

    # Ejecutar la función síncrona en un hilo separado
    return await asyncio.to_thread(_sync_authenticate)

# Similarmente, podríamos hacer async authenticate_admin si también se usa en rutas críticas
async def authenticate_admin(email: str, password: str) -> Tuple[bool, Dict[str, Any]]:
    """Autentica un administrador de marca (tabla 'brands')."""
    
    def _sync_authenticate_admin():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM brands WHERE email = %s",
                (email,)
            )
            admin = cursor.fetchone()
            
            if not admin:
                return False, {}
            
            is_valid = check_password(admin["password"], password)
            
            if not is_valid:
                return False, {}
            
            admin.pop("password", None)
            return True, admin
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
                
    return await asyncio.to_thread(_sync_authenticate_admin)

def register_corporate_admin_and_create_brand_link(admin_data: AdminRegister) -> Dict[str, Any]:
    """
    Registers a new corporate admin and ensures a corresponding brand entry exists.
    The 'brands' table entry will use the same name, email, and hashed password
    as the corporate admin for simplicity in this linked setup.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Check if corporate admin email already exists in corporate_admins table
        cursor.execute("SELECT id FROM corporate_admins WHERE email = %s", (admin_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corporate admin with this email already exists."
            )

        # 2. Create corporate admin in corporate_admins table
        hashed_password = hash_password(admin_data.password)  # Your existing function
        cursor.execute(
            "INSERT INTO corporate_admins (name, email, password, is_active) VALUES (%s, %s, %s, TRUE)",
            (admin_data.name, admin_data.email, hashed_password)
        )
        # corporate_admin_id = cursor.lastrowid # If you need the ID

        # 3. Ensure a corresponding brand entry exists in 'brands' table.
        # Using INSERT IGNORE: if a brand with this email already exists, it will be ignored.
        # This requires the 'email' column in the 'brands' table to have a UNIQUE constraint.
        # The name and password for the brand entry are taken from the corporate admin for simplicity.
        cursor.execute(
            """INSERT IGNORE INTO brands (name, email, password, created_at, updated_at) 
               VALUES (%s, %s, %s, NOW(), NOW())""",
            (admin_data.name, admin_data.email, hashed_password)
        )
        
        conn.commit()
        
        # 4. Return the created corporate admin's details (without password)
        cursor.execute("SELECT id, name, email, is_active FROM corporate_admins WHERE email = %s", (admin_data.email,))
        new_corp_admin = cursor.fetchone()
        if not new_corp_admin:
            # This should ideally not happen if the insert was successful
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve newly created corporate admin.")
        return new_corp_admin

    except mysql.connector.Error as err:
        conn.rollback()
        logger.error(f"Database error during corporate admin and brand link creation: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {err}"
        )
    except HTTPException as http_exc:
        conn.rollback()
        raise http_exc
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error during corporate admin and brand link creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
        
# --- NUEVA FUNCIÓN --- 
async def authenticate_corporate_admin(email: str, password: str) -> Tuple[bool, Dict[str, Any]]:
    """Autentica un administrador corporativo (tabla 'corporate_admins')."""
    
    def _sync_authenticate_corporate_admin():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM corporate_admins WHERE email = %s AND is_active = TRUE",
                (email,)
            )
            admin = cursor.fetchone()
            
            if not admin:
                return False, {}
            
            stored_hash = admin.get("password", "HASH_NO_ENCONTRADO_EN_DB")
            entered_password = password
            
            is_valid = check_password(stored_hash, entered_password)
            
            if not is_valid:
                return False, {}
            
            admin.pop("password", None)
            return True, admin
        except Error as e:
            print(f"Error durante la autenticación corporativa: {e}")
            return False, {}
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
                
    return await asyncio.to_thread(_sync_authenticate_corporate_admin)
# --- FIN NUEVA FUNCIÓN ---

def register_user(user_data: UserRegister) -> Dict[str, Any]:
    """Registra un nuevo usuario"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Verificar si el correo ya está registrado
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )
        
        # Verificar si la marca existe
        cursor.execute("SELECT id FROM marcas WHERE id = %s", (user_data.marca_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La marca especificada no existe"
            )
        
        # Crear usuario
        hashed_password = hash_password(user_data.password)
        cursor.execute(
            "INSERT INTO usuarios (marca_id, username, email, password, is_active, is_admin) "
            "VALUES (%s, %s, %s, %s, TRUE, %s)",
            (user_data.marca_id, user_data.username, user_data.email, hashed_password, 
             1 if user_data.is_admin else 0)
        )
        conn.commit()
        
        # Obtener usuario creado
        cursor.execute(
            "SELECT u.*, m.name as marca_name FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.email = %s",
            (user_data.email,)
        )
        user = cursor.fetchone()
        
        # Eliminar la contraseña antes de devolver los datos
        user.pop("password", None)
        return user
    finally:
        cursor.close()
        conn.close()

def register_admin(admin_data: AdminRegister) -> Dict[str, Any]:
    """Registra un nuevo administrador de marca (tabla 'brands')."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Verificar si el correo ya está registrado
        cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )
        
        # Crear administrador
        hashed_password = hash_password(admin_data.password)
        cursor.execute(
            "INSERT INTO brands (name, email, password) VALUES (%s, %s, %s)",
            (admin_data.name, admin_data.email, hashed_password)
        )
        conn.commit()
        
        # Obtener administrador creado
        cursor.execute("SELECT * FROM brands WHERE email = %s", (admin_data.email,))
        admin = cursor.fetchone()
        
        # Eliminar la contraseña antes de devolver los datos
        admin.pop("password", None)
        return admin
    finally:
        cursor.close()
        conn.close()

# Funciones para marcas
def get_marcas_by_admin(admin_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Obtiene las marcas administradas por un admin corporativo o de marca."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- ADDED: Look up target_brand_id from admin_data dictionary ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None # This will be the ID from the 'brands' table

    try:
        # Find the corporate admin's email
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()

        if not corp_admin_info:
             # Maybe it's a regular brand admin? Check the 'brands' table directly
             # This part assumes a regular 'admin' role also has a 'sub' with the brands.id
             # Adjust if the token structure for 'admin' role is different
             if admin_data.get("role") == "admin":
                 target_brand_id = admin_id_corp # Assuming 'sub' IS the brands.id for role 'admin'
                 logger.info(f"Admin role detected. Using brand_id directly: {target_brand_id}")
             else:
                # If not found in corporate_admins and not role 'admin', raise error
                logger.error(f"Corporate admin info not found for ID: {admin_id_corp}")
                raise HTTPException(status_code=404, detail="Admin profile not found.")
        else:
            # Found corporate admin, now find corresponding brands.id via email
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']
                logger.info(f"Found corresponding brand_id: {target_brand_id} for corporate admin email: {admin_email}")
            else:
                 logger.error(f"No corresponding 'brands' entry found for corporate admin email: {admin_email}")
                 # Decide how to handle: error or return empty list?
                 # Returning empty list might be safer if creation isn't guaranteed.
                 return []

        # Check if we successfully found a target_brand_id
        if target_brand_id is None:
             logger.error(f"Could not determine target_brand_id for admin data: {admin_data}")
             # Return empty list if no brand ID could be associated
             return []
        # --- END ADDED LOOKUP ---

        # Use the determined target_brand_id in the query
        logger.info(f"Querying marcas for target_brand_id: {target_brand_id}")
        cursor.execute(
            "SELECT m.*, "
            "(SELECT COUNT(*) FROM usuarios u WHERE u.marca_id = m.id) as user_count "
            "FROM marcas m "
            "WHERE m.brand_id = %s " # Filter by the correct target_brand_id
            "ORDER BY m.name ASC",
            (target_brand_id,)  # Pass the integer target_brand_id
        )
        results = cursor.fetchall()
        logger.info(f"Found {len(results)} marcas for brand_id {target_brand_id}")
        return results
    except Exception as e:
        # Log the error for more details
        logger.error(f"Error in get_marcas_by_admin for admin_data {admin_data}: {e}", exc_info=True)
        # Re-raise a generic server error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving brands."
        )
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def get_marca_by_id(marca_id: int, admin_id: int) -> Dict[str, Any]:
    """Obtiene una marca por su ID"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT * FROM marcas WHERE id = %s AND brand_id = %s",
            (marca_id, admin_id)
        )
        marca = cursor.fetchone()
        
        if not marca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Marca no encontrada"
            )
        
        return marca
    finally:
        cursor.close()
        conn.close()

def create_marca(marca_data: MarcaCreate, admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva marca"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Extract corporate admin details
    admin_id_corp = int(admin_data["sub"]) # This is the corporate_admins.id
    admin_email = None

    try:
        # --- NEW: Fetch the corporate admin's email to find the corresponding brands.id ---
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()
        if not corp_admin_info:
             raise HTTPException(status_code=404, detail="Corporate admin not found.")
        admin_email = corp_admin_info['email']

        # --- NEW: Look up the corresponding brands.id using the email ---
        cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
        brand_entry = cursor.fetchone()
        if not brand_entry:
            raise HTTPException(
                status_code=404,
                detail=f"No corresponding entry found in 'brands' table for admin email {admin_email}"
            )
        target_brand_id = brand_entry['id'] # This is the brands.id we need to use
        # --- END NEW ---

        # Verificar si ya existe una marca con el mismo nombre para este brand_id
        cursor.execute(
            "SELECT id FROM marcas WHERE name = %s AND brand_id = %s",
            (marca_data.name, target_brand_id) # Use the looked-up target_brand_id
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una marca con ese nombre para esta organización"
            )

        # Crear marca using the correct target_brand_id
        cursor.execute(
            "INSERT INTO marcas (brand_id, name, description) VALUES (%s, %s, %s)",
            (target_brand_id, marca_data.name, marca_data.description) # Use target_brand_id
        )
        conn.commit()

        # Obtener marca creada
        cursor.execute(
            "SELECT * FROM marcas WHERE id = LAST_INSERT_ID()"
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def update_marca(marca_id: int, marca_data: MarcaCreate, admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza una marca existente"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- ADDED: Look up target_brand_id similar to create_marca ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None

    try:
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()
        if corp_admin_info:
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']

        if not target_brand_id:
             raise HTTPException(status_code=404, detail="Could not determine the associated brand ID for the admin.")
        # --- END ADDED ---

        # Verificar si la marca existe y pertenece al brand_id del admin
        cursor.execute(
            "SELECT id FROM marcas WHERE id = %s AND brand_id = %s",
            (marca_id, target_brand_id) # Check against target_brand_id
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Marca no encontrada o no pertenece a esta organización"
            )

        # Verificar si ya existe otra marca con el mismo nombre para este brand_id
        cursor.execute(
            "SELECT id FROM marcas WHERE name = %s AND brand_id = %s AND id != %s",
            (marca_data.name, target_brand_id, marca_id) # Check against target_brand_id
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otra marca con ese nombre para esta organización"
            )

        # Actualizar marca
        cursor.execute(
            "UPDATE marcas SET name = %s, description = %s WHERE id = %s AND brand_id = %s", # Added brand_id check for safety
            (marca_data.name, marca_data.description, marca_id, target_brand_id)
        )
        conn.commit()

        # Obtener marca actualizada
        cursor.execute("SELECT * FROM marcas WHERE id = %s", (marca_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def delete_marca(marca_id: int, admin_data: Dict[str, Any]) -> bool:
    """Elimina una marca existente"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- ADDED: Look up target_brand_id similar to create_marca ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None

    try:
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,), dictionary=True) # Added dictionary=True temp
        corp_admin_info = cursor.fetchone()
        if corp_admin_info:
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,), dictionary=True) # Added dictionary=True temp
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']

        if not target_brand_id:
             raise HTTPException(status_code=404, detail="Could not determine the associated brand ID for the admin.")
        # --- END ADDED ---

        # Verificar si la marca existe y pertenece al brand_id del admin
        cursor.execute(
            "SELECT id FROM marcas WHERE id = %s AND brand_id = %s",
            (marca_id, target_brand_id) # Check against target_brand_id
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Marca no encontrada o no pertenece a esta organización"
            )

        # Eliminar marca
        cursor.execute("DELETE FROM marcas WHERE id = %s AND brand_id = %s", (marca_id, target_brand_id)) # Added brand_id check for safety
        conn.commit()

        # Check if deletion was successful
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()

# Funciones para usuarios (desde el panel de administración)
def get_usuarios_by_admin(admin_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Obtiene los usuarios gestionados por un admin"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- ADDED: Look up target_brand_id similar to create_marca ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None

    try:
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()
        if corp_admin_info:
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']

        if not target_brand_id:
             # If no brand ID found, the admin manages no users via this relationship
             return []
        # --- END ADDED ---


        cursor.execute(
            "SELECT u.id, u.marca_id, u.username, u.email, u.is_active, u.is_admin, u.created_at, u.updated_at, "
            "m.name as marca_name "
            "FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE m.brand_id = %s " # Filter by the correct target_brand_id
            "ORDER BY u.username ASC",
            (target_brand_id,)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def create_usuario(usuario_data: UserRegister, admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo usuario desde el panel de administración"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- ADDED: Look up target_brand_id similar to create_marca ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None

    try:
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()
        if corp_admin_info:
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']

        if not target_brand_id:
             raise HTTPException(status_code=404, detail="Could not determine the associated brand ID for the admin.")
        # --- END ADDED ---

        # Verificar si el correo ya está registrado
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (usuario_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )

        # Verificar si la marca especificada existe y pertenece al brand_id del admin
        cursor.execute(
            "SELECT id FROM marcas WHERE id = %s AND brand_id = %s",
            (usuario_data.marca_id, target_brand_id) # Check against target_brand_id
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La marca especificada no existe o no pertenece a esta organización"
            )

        # Crear usuario
        hashed_password = hash_password(usuario_data.password)
        cursor.execute(
            "INSERT INTO usuarios (marca_id, username, email, password, is_active, is_admin) "
            "VALUES (%s, %s, %s, %s, TRUE, %s)",
            (usuario_data.marca_id, usuario_data.username, usuario_data.email, hashed_password,
             1 if usuario_data.is_admin else 0)
        )
        conn.commit()

        # Obtener usuario creado
        cursor.execute(
            "SELECT u.*, m.name as marca_name FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.id = LAST_INSERT_ID()"
        )
        user = cursor.fetchone()

        # Eliminar la contraseña antes de devolver los datos
        user.pop("password", None)
        return user
    finally:
        cursor.close()
        conn.close()

def update_usuario(usuario_id: int, usuario_data: dict, admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza un usuario existente desde el panel de administración"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- ADDED: Look up target_brand_id similar to create_marca ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None

    try:
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()
        if corp_admin_info:
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']

        if not target_brand_id:
             raise HTTPException(status_code=404, detail="Could not determine the associated brand ID for the admin.")
        # --- END ADDED ---

        # Verificar si el usuario existe y pertenece a una marca del admin's brand_id
        cursor.execute(
            "SELECT u.id, u.marca_id, u.is_admin FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.id = %s AND m.brand_id = %s", # Check against target_brand_id
            (usuario_id, target_brand_id)
        )
        usuario = cursor.fetchone()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado o no pertenece a esta organización"
            )

        current_marca_id = usuario["marca_id"]
        is_currently_admin = usuario["is_admin"]

        # Determinar marca_id a usar (la actual o la nueva)
        new_target_marca_id = usuario_data.get("marca_id", current_marca_id)

        # Verificar si la marca especificada existe y pertenece al admin's brand_id
        if "marca_id" in usuario_data:
            cursor.execute(
                "SELECT id FROM marcas WHERE id = %s AND brand_id = %s",
                (usuario_data["marca_id"], target_brand_id) # Check against target_brand_id
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La marca especificada no existe o no pertenece a esta organización"
                )

        # Verificar si el correo ya está registrado para otro usuario
        if "email" in usuario_data:
            cursor.execute(
                "SELECT id FROM usuarios WHERE email = %s AND id != %s",
                (usuario_data["email"], usuario_id)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El correo electrónico ya está registrado por otro usuario"
                )

        # Manejar el cambio de estado de administrador
        if "is_admin" in usuario_data and usuario_data["is_admin"] != is_currently_admin:
            # Si se está activando como admin
            if usuario_data["is_admin"]:
                # Verificar si ya existe un administrador para esta marca
                cursor.execute(
                    "SELECT id FROM usuarios WHERE marca_id = %s AND is_admin = 1 AND id != %s",
                    (new_target_marca_id, usuario_id)
                )
                if cursor.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Ya existe un administrador para esta marca. Debe desasignar al actual antes de asignar uno nuevo."
                    )

        # Preparar la consulta de actualización
        update_fields = []
        params = []

        if "marca_id" in usuario_data:
            update_fields.append("marca_id = %s")
            params.append(usuario_data["marca_id"])

        if "username" in usuario_data:
            update_fields.append("username = %s")
            params.append(usuario_data["username"])

        if "email" in usuario_data:
            update_fields.append("email = %s")
            params.append(usuario_data["email"])

        if "password" in usuario_data and usuario_data["password"]:
            update_fields.append("password = %s")
            params.append(hash_password(usuario_data["password"]))

        if "is_active" in usuario_data:
            update_fields.append("is_active = %s")
            params.append(usuario_data["is_active"])

        if "is_admin" in usuario_data:
            update_fields.append("is_admin = %s")
            params.append(1 if usuario_data["is_admin"] else 0)

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron campos para actualizar"
            )

        # Ejecutar la actualización
        update_query = f"UPDATE usuarios SET {', '.join(update_fields)} WHERE id = %s"
        params.append(usuario_id)
        cursor.execute(update_query, params)
        conn.commit()

        # Obtener usuario actualizado
        cursor.execute(
            "SELECT u.id, u.marca_id, u.username, u.email, u.is_active, u.is_admin, u.created_at, u.updated_at, "
            "m.name as marca_name "
            "FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.id = %s",
            (usuario_id,)
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def toggle_usuario_status(usuario_id: int, admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """Activa o desactiva un usuario"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- ADDED: Look up target_brand_id similar to create_marca ---
    admin_id_corp = int(admin_data["sub"])
    admin_email = None
    target_brand_id = None

    try:
        cursor.execute("SELECT email FROM corporate_admins WHERE id = %s", (admin_id_corp,))
        corp_admin_info = cursor.fetchone()
        if corp_admin_info:
            admin_email = corp_admin_info['email']
            cursor.execute("SELECT id FROM brands WHERE email = %s", (admin_email,))
            brand_entry = cursor.fetchone()
            if brand_entry:
                target_brand_id = brand_entry['id']

        if not target_brand_id:
             raise HTTPException(status_code=404, detail="Could not determine the associated brand ID for the admin.")
        # --- END ADDED ---

        # Verificar si el usuario existe y pertenece a una marca del admin's brand_id
        cursor.execute(
            "SELECT u.id, u.is_active FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.id = %s AND m.brand_id = %s", # Check against target_brand_id
            (usuario_id, target_brand_id)
        )
        usuario = cursor.fetchone()

        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado o no pertenece a esta organización"
            )

        # Cambiar estado
        new_status = not usuario["is_active"]
        cursor.execute(
            "UPDATE usuarios SET is_active = %s WHERE id = %s",
            (new_status, usuario_id)
        )
        conn.commit()

        # Obtener usuario actualizado
        cursor.execute(
            "SELECT u.id, u.marca_id, u.username, u.email, u.is_active, u.created_at, u.updated_at, u.is_admin, " # Added is_admin
            "m.name as marca_name "
            "FROM usuarios u "
            "JOIN marcas m ON u.marca_id = m.id "
            "WHERE u.id = %s",
            (usuario_id,)
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

# --- Nueva función --- 
def get_marca_name_by_id(usuario_id: int) -> Optional[str]:
    """Obtiene el nombre de la marca asociada a un usuario por su ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    marca_name = None
    try:
        cursor.execute(
            "SELECT m.name FROM marcas m JOIN usuarios u ON m.id = u.marca_id WHERE u.id = %s",
            (usuario_id,)
        )
        result = cursor.fetchone()
        if result:
            marca_name = result.get('name')
    except Error as e:
        print(f"Error al obtener el nombre de la marca para usuario {usuario_id}: {e}")
        # Podrías lanzar una excepción aquí si prefieres manejar errores de forma más estricta
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return marca_name

# --- NUEVAS FUNCIONES PARA 2FA --- 

def generate_2fa_code(length: int = 6) -> str:
    """Genera un código numérico aleatorio."""
    return ''.join(random.choices(string.digits, k=length))

def send_2fa_email(recipient_email: str, code: str):
    """Envía el código 2FA por correo electrónico."""
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        print("ERROR: Faltan credenciales SMTP en .env. No se puede enviar correo 2FA.")
        # En producción, podrías querer lanzar una excepción aquí
        # o tener un manejo más robusto.
        return

    msg = EmailMessage()
    msg.set_content(f"Your Tama Insights verification code is: {code}\n\nThis code will expire in 5 minutes.")
    msg['Subject'] = 'Your Tama Insights 2FA Code'
    msg['From'] = SMTP_USER
    msg['To'] = recipient_email

    try:
        # Conectar al servidor SMTP
        # Usaremos STARTTLS ya que el puerto es 587
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls() # Iniciar conexión segura
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPAuthenticationError:
        print(f"ERROR: Fallo de autenticación SMTP para {SMTP_USER}. Verifica usuario/contraseña.")
    except smtplib.SMTPConnectError:
        print(f"ERROR: No se pudo conectar al servidor SMTP en {SMTP_HOST}:{SMTP_PORT}.")
    except Exception as e:
        print(f"ERROR: Ocurrió un error inesperado al enviar el correo 2FA: {e}")

def store_2fa_code(user_id: int, code: str):
    """Almacena el código 2FA en la base de datos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        # Invalidar códigos anteriores para el mismo usuario
        cursor.execute("UPDATE two_factor_codes SET is_used = TRUE WHERE user_id = %s AND is_used = FALSE", (user_id,))
        # Insertar el nuevo código
        cursor.execute(
            "INSERT INTO two_factor_codes (user_id, code, expires_at) VALUES (%s, %s, %s)",
            (user_id, code, expires_at)
        )
        conn.commit()
    except Error as e:
        print(f"Error al almacenar código 2FA para user_id {user_id}: {e}")
        conn.rollback() # Revertir cambios en caso de error
        raise # Re-lanzar la excepción para que el endpoint la maneje
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def verify_and_consume_2fa_code(user_id: int, submitted_code: str) -> bool:
    """Verifica el código 2FA y lo marca como usado si es válido."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Buscar un código válido y no usado
        cursor.execute(
            "SELECT id FROM two_factor_codes "
            "WHERE user_id = %s AND code = %s AND expires_at > UTC_TIMESTAMP() AND is_used = FALSE",
            (user_id, submitted_code)
        )
        valid_code = cursor.fetchone()

        if valid_code:
            # Marcar como usado
            cursor.execute("UPDATE two_factor_codes SET is_used = TRUE WHERE id = %s", (valid_code['id'],))
            conn.commit()
            return True
        else:
            return False
    except Error as e:
        print(f"Error al verificar código 2FA para user_id {user_id}: {e}")
        conn.rollback()
        return False # Devolver False en caso de error de DB
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# --- FIN NUEVAS FUNCIONES PARA 2FA ---