from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from embed import embed_text, query_unique
import json
import uvicorn
import os
import hashlib
import base64
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class Query(BaseModel):
    query: str
    num_results: int
    skip_urls: list = []
   

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.post("/query")
async def query_embeddings(query: Query):
    return await query_unique(query.query, query.num_results, skip_urls=query.skip_urls)


data_store = {}

class QueryData(BaseModel):
    data: list

@app.post("/generate/")
async def generate_page(query_data: QueryData):
    # convert to a string and hash it
    json_data = json.dumps(query_data.data)
    # Convert the query data to a string and hash it
    data_str = str(json_data).encode('utf-8')
    hash_object = hashlib.sha256(data_str)
    short_hash = base64.urlsafe_b64encode(hash_object.digest()).decode('utf-8')[:10]  # keeping it short

    print("Short hash: ", short_hash)
    
    # Store the data using the hash as a key
    data_store[short_hash] = query_data.data
    
    # Return the unique URL
    return {"url": f"http://localhost:8000/view/{short_hash}"}

@app.get("/view/{hash_id}")
async def view_page(hash_id: str, request: Request):
    # Lookup the data using the hash
    if hash_id in data_store:
        data = data_store[hash_id]
        # Here you would generate your HTML page using the data
        context = {"request": request, "data": data}
        
        return templates.TemplateResponse("base.html", context=context)
        # return {"data": data}
    else:
        context = {"request": request, "data": "No data found"}
        return templates.TemplateResponse("base.html", context=context)
        # raise HTTPException(status_code=404, detail="Not Found")


        
@app.get("/len")
async def len_posts():
    with open('posts_embedded.json', 'r') as f:
        posts = json.load(f)
    return len(posts)

# run the server with uvicorn main:app --reload

def start():
    port = int(os.environ.get("PORT", 8000))
    """Launched with `poetry run start` at root level"""
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    start()