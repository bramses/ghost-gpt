from fastapi import FastAPI
from pydantic import BaseModel
from embed import embed_text
import json
import uvicorn
import os
from sklearn.metrics.pairwise import cosine_similarity
from numpy import array


app = FastAPI()

class Query(BaseModel):
    query: str
    num_results: int
   

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

@app.post("/query")
async def create_item(query: Query):
    embedding = await embed_text(query.query)

    # read posts_embedded.json and find the post with the closest embedding using cosine similarity
    # return the post

    with open('posts_embedded.json', 'r') as f:
        posts = json.load(f)
        # filter out posts without embeddings
        posts = [post for post in posts if 'embedding' in post]
    for post in posts:
        vector_a = array(post['embedding']).reshape(1, -1)
        vector_b = array(embedding).reshape(1, -1)
        similarity = cosine_similarity(vector_a, vector_b)
        post['similarity'] = similarity[0][0]
    posts.sort(key=lambda x: x['similarity'], reverse=True)
    # fetch top results and get the plaintext and url
    results = []
    for i in range(query.num_results):
        results.append({
            'plaintext': posts[i]['plaintext'],
            'url': posts[i]['url'],
            'similarity': posts[i]['similarity']
        })
    return results
        

        
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