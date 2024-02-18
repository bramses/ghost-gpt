from supabase import create_client, Client
import os
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
POSTS_TABLE = os.getenv("SUPABASE_POSTS_TABLE")
PARAGRAPHS_TABLE = os.getenv("SUPABASE_PARAGRAPHS_TABLE")


supabase: Client = create_client(url, key)

def insert_row(data: dict, table: str = "data"):
    try:
        supabase.table(table).insert(data).execute()
    except Exception as e:
        print(e)
        return {"error": e}

def insert_post_and_paragraphs(post: dict):
    insert_row(post, "bramadams_dev_posts")
    if "paragraphs" not in post:
        return
    paragraphs = post["paragraphs"]
    for paragraph in paragraphs:
        paragraph["post_id"] = post["id"]
        # generate an id by combining the post url 
        insert_row(paragraph, "bramadams_dev_paragraphs")
    pass

def update_all_paragraphs_in_post(post_id: str, paragraphs: list):
    # delete all paragraphs with the post_id and then insert the new paragraphs
    pass

def update_post(post: dict):
    # update the post and all the paragraphs
    pass

def get_all_updated_posts():
    # get all the posts that have been updated by seeing if updated_at is greater than the supabase updated_at
    pass

def read_json(file: str):
    with open(file, "r") as f:
        read_file = f.read()
        return json.loads(read_file)
    
async def semantic_search(embedding: list, match_threshold: float, match_count: int):
    # get the embedding of the text
    res = supabase.rpc("match_paragraphs", {"query_embedding": embedding, "match_threshold": match_threshold, "match_count": match_count}).execute()
    return res
    
INSERT = False

def main():
    if INSERT:
        data = read_json("posts_embedded.json")
        # pretty print the data
        print(json.dumps(data[0], indent=4))
        i = 0
        for i in range(len(data)):
            insert_post_and_paragraphs(data[i])
            i += 1
    else:
        # asyncio.run(semantic_search("test", 0.2, 3))
        pass


if __name__ == "__main__":
    main()    
