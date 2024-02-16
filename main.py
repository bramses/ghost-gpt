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
   

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.post("/query")
async def query_embeddings(query: Query):
    return await query_unique(query.query, query.num_results)

'''
given data like:

[
  {
    "paragraph": "* childish gambino had an interview about some meme that was going around in 2013 on vine and how sad it is to make art to maintain success instead of chasing your own curiosity. he follows through on that to this day.",
    "url": "https://www.bramadams.dev/my-thoughts-on-excellent-advice-for-living#:~:text=childish%20gambino%20had%20an%20interview%20about%20some%20meme%20that%20was%20going%20around%20in%202013%20on%20vine%20and%20how%20sad%20it%20is%20to%20make%20art%20to%20maintain%20success",
    "similarity": 0.5516542627319667
  },
  {
    "paragraph": "When I was a child, old enough to desire privacy, but young enough that most worldly things and I were on a first time basis -- on a birthday evening my friends and I were playing video games a drunken twenty-something stumbled into our house's back door. ^198d6d",
    "url": "https://www.bramadams.dev/202212212242#:~:text=When%20I%20was%20a%20child%2C%20old%20enough%20to%20desire%20privacy%2C%20but%20young%20enough%20that%20most%20worldly%20things%20and%20I%20were%20on%20a%20first%20time%20basis%20--%20on%20a",
    "similarity": 0.40297942353510174
  }
]

i want to create a unique url that will return a template html page with the paragraphs and urls in a list

the url should be short and unique and not contain any special characters

the url should be unique to the query and the results

ex: http://localhost:8000/big-fish-super

the html page should be a template with the query and the results in a list
'''

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