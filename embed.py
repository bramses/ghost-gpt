import os
import json
import asyncio
import tiktoken
import urllib.parse
import time

enc = tiktoken.get_encoding("cl100k_base")

from dotenv import load_dotenv
load_dotenv()

MIN_PARAGRAPH_LENGTH = 100
SKIP_LIST = [
    "bramadams.dev is a reader-supported published Zettelkasten. Both free and paid subscriptions are available. If you want to support my work, the best way is by taking out a paid subscription."
]

from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def create_text_fragment_url(base_url, text, max_length=140):
    if text.startswith('*'):
        text = text.lstrip('*').strip()
        text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
        last_space_index = text.rfind(' ')
        if last_space_index > -1:
            text = text[:last_space_index]
    encoded_text = urllib.parse.quote(text)
    return f"{base_url}#:~:text={encoded_text}"

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
            if len(post['plaintext']) > 0:
                url = post['url']
                # split post by paragraphs
                paragraphs = post['plaintext'].split('\n')
                # embed each paragraph into { paragraph: paragraph, embedding: embedding, url: url }
                post['paragraphs'] = []
                for paragraph in paragraphs:
                    if len(paragraph) > MIN_PARAGRAPH_LENGTH and paragraph not in SKIP_LIST:
                        embedding = await embed_text(paragraph.strip())
                        text_fragment_url = create_text_fragment_url(url, paragraph.strip())
                        post['paragraphs'].append({
                            'paragraph': paragraph.strip(),
                            'embedding': embedding,
                            'url': text_fragment_url,
                            'root_url': url
                        })

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