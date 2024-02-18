from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from embed import embed_text, query_unique
import json
import uvicorn
import os
import hashlib
import base64
from fastapi.templating import Jinja2Templates
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

IS_PROD = os.getenv("IS_PROD") == "True"

class Query(BaseModel):
    query: str
    num_results: int
    skip_urls: list = []
    parent_hash: str = None


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


@app.post("/query")
async def query_embeddings(query: Query):
    if query.num_results > 4:
        raise HTTPException(status_code=400, detail="Number of results must be less than 4")
    if query.num_results <= 0:
        raise HTTPException(status_code=400, detail="Number of results must be greater than 0")
    if len(query.query) <= 0:
        raise HTTPException(status_code=400, detail="Query must not be empty")
    if len(query.query) >= 1000:
        raise HTTPException(status_code=400, detail="Query must be less than 1000 characters")
    
    
    ''' 
    if a parent hash id is provided, then we need to add the data to the parent hash id in the data store, else we need to create a new hash id and add the data to the data store
    '''

    if query.parent_hash is not None and query.parent_hash != "":
        if query.parent_hash in data_store:
            data = await query_unique(query.query, query.num_results, skip_urls=query.skip_urls)

            data_store[query.parent_hash]['data'].extend(data)
            if IS_PROD:
                url = os.getenv("PROD_URL")
                print("Using prod url")
            else:
                url = "http://0.0.0.0:8000"
            return {
                "url": f"{url}/view/{query.parent_hash}",
                "data": data_store[query.parent_hash]['data']
            }
        else:
            raise HTTPException(status_code=404, detail="Parent hash not found")
    else:
        data = await query_unique(query.query, query.num_results, skip_urls=query.skip_urls)

        json_data = json.dumps(data)
        # Convert the query data to a string and hash it
        data_str = str(json_data).encode('utf-8')
        hash_object = hashlib.sha256(data_str)
        short_hash = base64.urlsafe_b64encode(
            hash_object.digest()).decode('utf-8')[:10]  # keeping it short

        print("Short hash added: ", short_hash)

        # Store the data using the hash as a key
        data_store[short_hash] = {
            "data": data,
            "query": query.query
        }

        # Return the unique URL

        if IS_PROD:
            url = os.getenv("PROD_URL")
            print("Using prod url")
        else:
            url = "http://0.0.0.0:8000"

        return {
            "url": f"{url}/view/{short_hash}",
            "data": data
        }

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
    short_hash = base64.urlsafe_b64encode(
        hash_object.digest()).decode('utf-8')[:10]  # keeping it short

    print("Short hash: ", short_hash)

    # Store the data using the hash as a key
    data_store[short_hash] = query_data.data

    # Return the unique URL
    if IS_PROD:
        url = os.getenv("PROD_URL")
        print("Using prod url")
    else:
        url = "http://0.0.0.0:8000"
    return {"url": f"{url}/view/{short_hash}"}


@app.get("/view/{hash_id}")
async def view_page(hash_id: str, request: Request):
    # Lookup the data using the hash

    example_data = {
        "query": "What are some interesting facts about plants?",
        "data": [
            {
                "paragraph": "This is a solvable problem, where is the startup that fills my house with self-managing plants? https://t.co/tsZrynx4rB",
                "url": "https://www.bramadams.dev/202302281157#:~:text=This%20is%20a%20solvable%20problem%2C%20where%20is%20the%20startup%20that%20fills%20my%20house%20with%20self-managing%20plants%3F%20https%3A//t.co/tsZrynx4rB",
                "similarity": 0.27090848582538846,
                "next_pointer": "How do underwater plants in an aquarium contribute to the ecosystem, particularly in terms of oxygen production and water purification?"
            },
            {
                "paragraph": "Plants are great chemists—and alchemists, for that matter: they can turn sunbeams into matter! They have evolved to use biological warfare to repel predators—poisoning, paralyzing, or disorienting them—or to reduce their own digestibility to stay alive and protect their seeds, enhancing the chances that their species will endure.",
                "url": "https://www.bramadams.dev/202308032252#:~:text=Plants%20are%20great%20chemists%E2%80%94and%20alchemists%2C%20for%20that%20matter%3A%20they%20can%20turn%20sunbeams%20into%20matter%21%20They%20have%20evolved%20to%20use%20biological%20warfare",
                "similarity": 0.2603134188753087,
                "next_pointer": "How do carnivorous plants like the Venus Flytrap identify and trap their prey?"
            },
            {
                "paragraph": "It took the end of World War II to merge the entire planet into a single system and transform the global ocean into one gigantic safe, navigable waterway. (Location 4539)",
                "url": "https://www.bramadams.dev/202306112146#:~:text=It%20took%20the%20end%20of%20World%20War%20II%20to%20merge%20the%20entire%20planet%20into%20a%20single%20system%20and%20transform%20the%20global%20ocean%20into%20one%20gigantic%20safe%2C",
                "similarity": 0.25404196887954567,
                "next_pointer": "How do international maritime laws regulate shipping lanes to prevent disputes between countries?"
            }
        ]
    }

    if hash_id in data_store:
        data = data_store[hash_id]
        # Here you would generate your HTML page using the data
        context = {"request": request, "data": data}

        return templates.TemplateResponse("base.html", context=context)
        # return {"data": data}
    elif hash_id == "example":
        context = {"request": request, "data": example_data}
        return templates.TemplateResponse("base.html", context=context)
        # raise HTTPException(status_code=404, detail="Not Found")
    else:
        raise HTTPException(status_code=404, detail="Not Found")


@app.get("/len")
async def len_posts():
    with open('posts_embedded.json', 'r') as f:
        posts = json.load(f)
    return len(posts)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="bramadams.dev chat mode",
        version="3.0.2",
        description="Chat with bramadams.dev",
        routes=app.routes,
    )    

    if IS_PROD:
        openapi_schema["servers"] = [{
            "url": os.getenv("PROD_URL"),
        }]
    else:
        openapi_schema["servers"] = [
            {"url": "http://0.0.0.0:8000", "description": "Local server"},
            {"url": os.getenv("PROD_URL"), "description": "Production server"},
        ]
    # if components.schema is not defined add it (for openai error: Error getting system message: {"message":"Could not parse OpenAPI spec for plugin: ['In components section, schemas subsection is not an object']"})
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
        openapi_schema["components"]["schemas"] = {}
    else:
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

def start():
    port = int(os.environ.get("PORT", 8000))
    """Launched with `poetry run start` at root level"""
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    start()
