from contextlib import asynccontextmanager
import ngrok
from fastapi import FastAPI, Request
from loguru import logger
import os
import glob
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import uvicorn
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv() 


NGROK_AUTH_TOKEN = os.environ['NGROK_AUTH_TOKEN']
APPLICATION_PORT = os.environ['APPLICATION_PORT']
HTTPS_SERVER = os.environ['HTTPS_SERVER']
DEPLOY_DOMAIN = os.environ['DEPLOY_DOMAIN']


origins = [
    "http://mullet-immortal-labrador.ngrok-free.app/",
    "https://mullet-immortal-labrador.ngrok-free.app/",
    "http://localhost",
    "http://localhost:8080/",
    "http://localhost:8000/",
    "http://127.0.0.1:8000/",
    "http://127.0.0.1:8000"
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    proto: "http", "tcp", "tls", "labeled"
    """
    logger.info("Setting up Ngrok Tunnel")
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    ngrok.forward(addr = HTTPS_SERVER+':'+str(APPLICATION_PORT),
                  proto = "http",
                  domain = DEPLOY_DOMAIN
                  )
    
    yield
    logger.info("Tearing Down Ngrok Tunnel")
    ngrok.disconnect()


app = FastAPI(lifespan=lifespan)

app.add_middleware(CORSMiddleware, 
                   allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"]
                   )

@app.get(path= "/",
         response_class=JSONResponse)
async def homepage_router(request: Request):
    return JSONResponse(content="wellcome", status_code= 200)


async def main():
    config = uvicorn.Config("main:app",
                            host=HTTPS_SERVER,
                            port=int(APPLICATION_PORT),
                            reload=True,
                            log_level="info",
                            )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())