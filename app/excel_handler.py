import os
import pandas as pd
from .utils import file_lock, get_temp_path
import ibm_boto3
from ibm_botocore.client import Config
from typing import Optional

# Local path where trabajamos
EXCEL_LOCAL_PATH = "data/employees.xlsx"
EXCEL_OBJECT_NAME = os.getenv("EXCEL_OBJECT_NAME", "employees.xlsx")
COS_BUCKET = os.getenv("COS_BUCKET")

def get_cos_client():
    endpoint = os.getenv("COS_ENDPOINT")
    api_key = os.getenv("COS_API_KEY")
    resource_instance_id = os.getenv("COS_RESOURCE_INSTANCE_ID", None)
    if not endpoint or not api_key or not COS_BUCKET:
        raise RuntimeError("Variables COS no configuradas: COS_ENDPOINT/COS_API_KEY/COS_BUCKET necesarias.")
    return ibm_boto3.client(
        "s3",
        ibm_api_key_id=api_key,
        ibm_service_instance_id=resource_instance_id or None,
        config=Config(signature_version="oauth"),
        endpoint_url=endpoint
    )

def download_from_cos() -> bool:
    """Descarga EXCEL_OBJECT_NAME desde COS a EXCEL_LOCAL_PATH. Retorna True si la descarga fue exitosa."""
    try:
        cos = get_cos_client()
        os.makedirs(os.path.dirname(EXCEL_LOCAL_PATH), exist_ok=True)
        tmp = get_temp_path(EXCEL_OBJECT_NAME)
        with open(tmp, "wb") as f:
            cos.download_fileobj(COS_BUCKET, EXCEL_OBJECT_NAME, f)
        os.replace(tmp, EXCEL_LOCAL_PATH)
        print("Descargado desde COS:", EXCEL_LOCAL_PATH)
        return True
    except Exception as e:
        print("No se pudo descargar desde COS (puede que el objeto no exista aún):", e)
        return False

def upload_to_cos() -> bool:
    """Sube EXCEL_LOCAL_PATH a COS (EXCEL_OBJECT_NAME)."""
    try:
        cos = get_cos_client()
        with open(EXCEL_LOCAL_PATH, "rb") as f:
            cos.upload_fileobj(f, COS_BUCKET, EXCEL_OBJECT_NAME)
        print("Subido a COS:", EXCEL_OBJECT_NAME)
        return True
    except Exception as e:
        print("Error subiendo a COS:", e)
        return False

def read_excel() -> pd.DataFrame:
    # Si no existe local, intentar descargar
    if not os.path.exists(EXCEL_LOCAL_PATH):
        download_from_cos()
    if not os.path.exists(EXCEL_LOCAL_PATH):
        cols = ["ID","Name","TimeOffBalance","Job","Address","RequestedTimeOff"]
        df = pd.DataFrame(columns=cols)
        df.to_excel(EXCEL_LOCAL_PATH, index=False)
    return pd.read_excel(EXCEL_LOCAL_PATH)

def write_excel(df: pd.DataFrame):
    with file_lock:
        tmp = get_temp_path("employees_working.xlsx")
        df.to_excel(tmp, index=False)
        os.replace(tmp, EXCEL_LOCAL_PATH)
        # intentar subir (si falla, no rompe la app)
        upload_to_cos()

def list_employees() -> pd.DataFrame:
    return read_excel()

def get_employee_by_id(emp_id: int) -> Optional[dict]:
    df = read_excel()
    row = df.loc[df['ID'] == emp_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()

def add_employee(data: dict) -> int:
    with file_lock:
        df = read_excel()
        if "ID" not in data or data.get("ID") is None:
            next_id = 1 if df.empty else int(df['ID'].max()) + 1
            data["ID"] = next_id
        else:
            if int(data["ID"]) in df['ID'].values:
                raise ValueError("ID ya existe.")
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        write_excel(df)
        return data["ID"]

def update_employee(emp_id: int, updates: dict) -> bool:
    with file_lock:
        df = read_excel()
        if emp_id not in df['ID'].values:
            return False
        for k, v in updates.items():
            if k in df.columns and v is not None:
                df.loc[df['ID'] == emp_id, k] = v
        write_excel(df)
        return True

def delete_employee(emp_id: int) -> bool:
    with file_lock:
        df = read_excel()
        if emp_id not in df['ID'].values:
            return False
        df = df[df['ID'] != emp_id]
        write_excel(df)
        return True
