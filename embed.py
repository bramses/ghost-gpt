from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import asyncio
import tiktoken
import urllib.parse
import time
from sklearn.metrics.pairwise import cosine_similarity
from numpy import array
from supabase_utils import semantic_search

enc = tiktoken.get_encoding("cl100k_base")

load_dotenv(override=True)

MIN_PARAGRAPH_LENGTH = 100
SKIP_LIST = [
    "bramadams.dev is a reader-supported published Zettelkasten. Both free and paid subscriptions are available. If you want to support my work, the best way is by taking out a paid subscription."
]


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


async def embed_posts(posts, dry_run=False):
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
                        if not dry_run:
                            embedding = await embed_text(paragraph.strip())
                        text_fragment_url = create_text_fragment_url(
                            url, paragraph.strip())
                        if not dry_run:
                            post['paragraphs'].append({
                                'paragraph': paragraph.strip(),
                                'embedding': embedding,
                                'url': text_fragment_url,
                                'root_url': url
                            })
                        else:
                            post['paragraphs'].append({
                                'paragraph': paragraph.strip(),
                                'embedding': None,
                                'url': text_fragment_url,
                                'root_url': url
                            })

    return posts


async def chat_completion(messages):
    completion = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages
    )
    return completion.choices[0].message.content


async def query_unique(query, n=5, hyp_question=False, unr_question=True, skip_urls=[]):
    embedding = await embed_text(query)
    sr = await semantic_search(embedding, 0.2, 10)

    clean_matches = []
    # read seed.txt file
    # with open('seed.txt', 'r') as f:
    #     seed = f.read()
    i = 0
    while i < n and i < len(sr.data):
        print(f"Processing {i+1}/{n}")
        print(f"URL: {sr.data[i]}")
        root_url = sr.data[i]['url'].split('#:~:text=')[0]
        if root_url in skip_urls:
            print(f"Skipping {sr.data[i]['url']}")
            n += 1
            i += 1
            continue
        if hyp_question:
            hypothetical_question = [
                {"role": "system", "content": f"Generate a hypothetical question using the prose from the seed.txt file as a style guide. The question should be related to the query.\n\nSeed: polemic poetry, thought-provoking prose, and the occasional pun."},
                {"role": "user", "content": f"Query: {sr.data[i]['paragraph']} "}
            ]
            
            next_pointer = await chat_completion(hypothetical_question)

            clean_matches.append({
                'paragraph': sr.data[i]['paragraph'],
                'url': sr.data[i]['url'],
                'similarity': sr.data[i]['similarity'],
                'next_pointer': next_pointer
            })
        elif unr_question:
            unrelated_question = [
                {"role": "system", "content": f"1. use the following as a seed 2. come up with an unrelated next question to explore something else. 3. make sure the question is related to the query by broad topic but unrelated as in it seems random. Just write the question -- nothing else."},
                {"role": "user", "content": f"Query: {sr.data[i]['paragraph']} "}
            ]
            
            next_pointer = await chat_completion(unrelated_question)

            clean_matches.append({
                'paragraph': sr.data[i]['paragraph'],
                'url': sr.data[i]['url'],
                'similarity': sr.data[i]['similarity'],
                'next_pointer': next_pointer
            })
        else:
            clean_matches.append({
                'paragraph': sr.data[i]['paragraph'],
                'url': sr.data[i]['url'],
                'similarity': sr.data[i]['similarity']
            })
        i += 1

    return clean_matches

async def query_unique_v0(query, n=5, hyp_question=False, unr_question=True, skip_urls=[]):
    embedding = await embed_text(query)

    # read posts_embedded.json and find the post with the closest embedding using cosine similarity
    # return the post

    # run the cosine similarity on the embeddings of the posts and store the top n matches
    highest_similarity_matches = []

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
    highest_similarity_matches.sort(
        key=lambda x: x['similarity'], reverse=True)
    clean_matches = []

    # read seed.txt file
    with open('seed.txt', 'r') as f:
        seed = f.read()

    i = 0
    while i < n and i < len(highest_similarity_matches):
        root_url = highest_similarity_matches[i]['url'].split('#:~:text=')[0]
        if root_url in skip_urls:
            print(f"Skipping {highest_similarity_matches[i]['url']}")
            n += 1
            i += 1
            continue
        if hyp_question:
            hypothetical_question = [
                {"role": "system", "content": f"Generate a hypothetical question using the prose from the seed.txt file as a style guide. The question should be related to the query.\n\nSeed: {seed}"},
                {"role": "user", "content": f"Query: {highest_similarity_matches[i]['paragraph']} "}
            ]
            
            next_pointer = await chat_completion(hypothetical_question)

            clean_matches.append({
                'paragraph': highest_similarity_matches[i]['paragraph'],
                'url': highest_similarity_matches[i]['url'],
                'similarity': highest_similarity_matches[i]['similarity'],
                'next_pointer': next_pointer
            })
        elif unr_question:
            unrelated_question = [
                {"role": "system", "content": f"1. use the following as a seed 2. come up with an unrelated next question to explore something else. 3. make sure the question is related to the query by broad topic but unrelated as in it seems random. Just write the question -- nothing else."},
                {"role": "user", "content": f"Query: {highest_similarity_matches[i]['paragraph']} "}
            ]
            
            next_pointer = await chat_completion(unrelated_question)

            clean_matches.append({
                'paragraph': highest_similarity_matches[i]['paragraph'],
                'url': highest_similarity_matches[i]['url'],
                'similarity': highest_similarity_matches[i]['similarity'],
                'next_pointer': next_pointer
            })
        else:
            clean_matches.append({
                'paragraph': highest_similarity_matches[i]['paragraph'],
                'url': highest_similarity_matches[i]['url'],
                'similarity': highest_similarity_matches[i]['similarity']
            })
        i += 1

    return clean_matches

if __name__ == "__main__":
    # get argv[1] as the file to embed python embed.py posts.json
    file_to_embed = os.sys.argv[1]
    with open(file_to_embed, 'r') as f:
        posts = json.load(f)
    posts = asyncio.run(embed_posts(posts))

    # write the embedded posts to a new file posts_embedded.json pretty printed
    with open('posts_embedded.embedbig.json', 'w') as f:
        json.dump(posts, f, indent=4, sort_keys=True)
