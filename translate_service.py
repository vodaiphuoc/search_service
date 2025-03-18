from googletrans import Translator
import asyncio
from contextlib import asynccontextmanager
import json

class TranslateEngine(object):
    def __init__(self):
        self._trans = Translator()
    
    async def translate(self, query:str):
        translated = self._trans.translate(query, src= "vi", dest= "en")
        result = await translated
        return result.text


from fastapi import FastAPI, Request, Response, Body
from fastapi.responses import JSONResponse
from typing import Annotated
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.translate_engine = TranslateEngine()

    yield
    app.translate_engine = None

app = FastAPI(lifespan = lifespan)

@app.post("/", response_class=JSONResponse)
async def index(query: Annotated[str, Body()], request: Request):
    query_text = json.loads(query)['query']

    result = await request.app.translate_engine.translate(query_text)

    return JSONResponse(
        status_code = 200, 
        content = {
            "translated_text": result
        }
    )


async def main_run():
    config = uvicorn.Config("translate_service:app", 
    	port=8080, 
    	log_level="info", 
    	reload=True,
    	)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main_run())