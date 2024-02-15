import os
import json
import asyncio
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def tokenize(text):
    return enc.encode(text)

def len_tokenized(text):
    return len(tokenize(text))

async def embed_text(text):
    print(f"Embedding: {text}")
    assert len(text) > 0
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

async def embed_posts(posts):
    for post in posts:
        if 'plaintext' in post and post['plaintext'] != "" and post['plaintext'] != None:
            if len(post['plaintext']) > 0 and len_tokenized(post['plaintext']) < 8191:
                post['embedding'] = await embed_text(post['plaintext'])
    return posts

if __name__ == "__main__":
    # get argv[1] as the file to embed python embed.py posts.json
    file_to_embed = os.sys.argv[1]
    with open(file_to_embed, 'r') as f:
        posts = json.load(f)
    posts = asyncio.run(embed_posts(posts))

    # write the embedded posts to a new file posts_embedded.json pretty printed
    with open('posts_embedded.json', 'w') as f:
        json.dump(posts, f, indent=4, sort_keys=True)