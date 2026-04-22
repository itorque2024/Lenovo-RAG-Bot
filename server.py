from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Lenovo Data Server")

API_KEY = os.getenv("INTERNAL_API_KEY", "default_secret_key")
api_key_header = APIKeyHeader(name="X-API-KEY")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

BASE_DIR = os.getcwd()
FOLDERS = ["tech", "policy", "product"]

@app.get("/", dependencies=[Depends(get_api_key)])
async def root():
    files = {}
    for folder in FOLDERS:
        if os.path.exists(folder):
            files[folder] = [f for f in os.listdir(folder) if f.endswith('.txt')]
    return {
        "message": "Lenovo Data Server is Online",
        "available_files": files,
        "usage": "Use /files/{folder}/{filename} to fetch content"
    }

@app.get("/files/{folder}/{filename}", dependencies=[Depends(get_api_key)])
async def get_file(folder: str, filename: str):
    if folder not in FOLDERS:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    file_path = os.path.join(BASE_DIR, folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

@app.get("/list", dependencies=[Depends(get_api_key)])
async def list_files():
    files = {}
    for folder in FOLDERS:
        if os.path.exists(folder):
            files[folder] = os.listdir(folder)
    return files

@app.get("/tools/validate-sn/{sn}", dependencies=[Depends(get_api_key)])
async def validate_sn(sn: str):
    # Lenovo serial numbers are usually 8 characters, alphanumeric
    is_valid = len(sn) == 8 and sn.isalnum()
    return {
        "serial_number": sn,
        "is_valid_format": is_valid,
        "message": "Format is correct (8 alphanumeric characters)" if is_valid else "Invalid format. Lenovo SNs are usually 8 alphanumeric characters."
    }

@app.get("/tools/convert-price/{usd_amount}", dependencies=[Depends(get_api_key)])
async def convert_price(usd_amount: float):
    # Mock conversion (you can connect to a real API in n8n)
    # Using a fixed rate for demo purposes (1 USD = 1.35 SGD)
    rate = 1.35 
    sgd_amount = round(usd_amount * rate, 2)
    return {
        "usd": usd_amount,
        "sgd": sgd_amount,
        "rate": rate,
        "currency": "SGD"
    }

if __name__ == "__main__":
    import uvicorn
    # Changed to 127.0.0.1 for security (Localhost only)
    uvicorn.run(app, host="127.0.0.1", port=8000)
