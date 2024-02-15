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

    highest_similarity_matches = [] # runt the cosine similarity on the embeddings of the posts and store the top n matches

    with open('posts_embedded.json', 'r') as f:
        posts = json.load(f)
        # filter out posts without paragraphs
        posts = [post for post in posts if 'paragraphs' in post]
    for post in posts:        
        for paragraph in post['paragraphs']:
            vector_a = array(paragraph['embedding']).reshape(1, -1)
            vector_b = array(embedding).reshape(1, -1)
            similarity = cosine_similarity(vector_a, vector_b)
            paragraph['similarity'] = similarity[0][0]
            highest_similarity_matches.append(paragraph)
    highest_similarity_matches.sort(key=lambda x: x['similarity'], reverse=True)
    clean_matches = []
    for i in range(query.num_results):
        clean_matches.append({
            'paragraph': highest_similarity_matches[i]['paragraph'],
            'url': highest_similarity_matches[i]['url'],
            'similarity': highest_similarity_matches[i]['similarity']
        })

    return clean_matches

        

        
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