import os
import pandas as pd
from io import BytesIO
import ibm_boto3
from ibm_botocore.client import Config
from typing import Optional
from .utils import file_lock, get_temp_path

EXCEL_LOCAL_PATH = "data/employees.xlsx"
# Nombre del objeto en COS (por ejemplo 'employees.xlsx')
EXCEL_OBJECT_NAME = os.getenv("EXCEL_OBJECT_NAME", "employees.xlsx")

def get_cos_client():
    endpoint = os.getenv("COS_ENDPOINT")
    api_key = os.getenv("COS_API_KEY")
    resource_instance_id = os.getenv("COS_RESOURCE_INSTANCE_ID", "")
    if not endpoint or not api_key:
        raise RuntimeError("Faltan variables de entorno COS (COS_ENDPOINT/COS_API_KEY).")
    return ibm_boto3.client(
        "s3",
        ibm_api_key_id=api_key,
        ibm_service_instance_id=resource_instance_id or None,
        config=Config(signature_version="oauth"),
        endpoint_url=endpoint
    )

def download_from_cos():
    """
    Descarga el objeto EXCEL_OBJECT_NAME desde COS al path data/employees.xlsx
    Si no existe en COS, deja el archivo local si está.
    """
    try:
        cos = get_cos_client()
        local_dir = os.path.dirname(EXCEL_LOCAL_PATH)
        os.makedirs(local_dir, exist_ok=True)
        # Obtenemos el archivo en memoria y lo guardamos localmente
        tmp_path = get_temp_path(EXCEL_OBJECT_NAME)
        with open(tmp_path, "wb") as f:
            cos.download_fileobj(os.getenv("COS_BUCKET"), EXCEL_OBJECT_NAME, f)
        # Mover a destino
        os.replace(tmp_path, EXCEL_LOCAL_PATH)
        return True
    except Exception as e:
        # Si falla (objeto no existe o credenciales), retornamos False
        # Esto permite iniciar con un archivo local en /data para testing
        print("Warning: descarga COS fallida:", e)
        return False

def upload_to_cos():
    """
    Sube el archivo local EXCEL_LOCAL_PATH al COS con nombre EXCEL_OBJECT_NAME.
    """
    try:
        cos = get_cos_client()
        with open(EXCEL_LOCAL_PATH, "rb") as f:
            cos.upload_fileobj(f, os.getenv("COS_BUCKET"), EXCEL_OBJECT_NAME)
        return True
    except Exception as e:
        print("Warning: subida a COS fallida:", e)
        return False

def read_excel() -> pd.DataFrame:
    if not os.path.exists(EXCEL_LOCAL_PATH):
        # intenta descargar desde COS si no existe local
        download_from_cos()
    if not os.path.exists(EXCEL_LOCAL_PATH):
        # crear un DataFrame vacío con columnas esperadas
        cols = ["ID","Name","TimeOffBalance","Job","Address","RequestedTimeOff"]
        df = pd.DataFrame(columns=cols)
        df.to_excel(EXCEL_LOCAL_PATH, index=False)
    return pd.read_excel(EXCEL_LOCAL_PATH)

def write_excel(df: pd.DataFrame):
    # Escritura atómica con lock
    with file_lock:
        tmp = get_temp_path("employees_working.xlsx")
        df.to_excel(tmp, index=False)
        os.replace(tmp, EXCEL_LOCAL_PATH)
        # subir a COS (intento, si falla no rompe)
        upload_to_cos()

def list_employees():
    df = read_excel()
    return df

def get_employee_by_id(emp_id: int) -> Optional[pd.Series]:
    df = read_excel()
    row = df.loc[df['ID'] == emp_id]
    if row.empty:
        return None
    return row.iloc[0]

def add_employee(data: dict):
    with file_lock:
        df = read_excel()
        # Generar ID si no viene
        if "ID" not in data or data.get("ID") is None:
            # generamos next ID max+1
            if df.empty:
                next_id = 1
            else:
                next_id = int(df['ID'].max()) + 1
            data["ID"] = next_id
        else:
            # verificar unicidad
            if int(data["ID"]) in df['ID'].values:
                raise ValueError("ID ya existe.")
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        write_excel(df)
        return data["ID"]

def update_employee(emp_id: int, updates: dict):
    with file_lock:
        df = read_excel()
        if emp_id not in df['ID'].values:
            return False
        for k, v in updates.items():
            if k in df.columns and v is not None:
                df.loc[df['ID'] == emp_id, k] = v
        write_excel(df)
        return True

def delete_employee(emp_id: int):
    with file_lock:
        df = read_excel()
        if emp_id not in df['ID'].values:
            return False
        df = df[df['ID'] != emp_id]
        write_excel(df)
        return True
