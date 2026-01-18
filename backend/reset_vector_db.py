
import os
import time
from pinecone import Pinecone
from dotenv import load_dotenv
import pathlib

# Load env
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
if not env_path.exists():
    load_dotenv()

def reset_db():
    api_key = os.getenv('PINECONE_API_KEY')
    index_name = os.getenv('PINECONE_INDEX', 'lumina-sales-agent')
    
    if not api_key:
        print("Error: PINECONE_API_KEY not found.")
        return

    pc = Pinecone(api_key=api_key)
    
    # List indexes
    indexes = [idx.name for idx in pc.list_indexes()]
    print(f"Current Pinecone Indexes: {indexes}")
    
    if index_name in indexes:
        print(f"Deleting existing index: {index_name}...")
        pc.delete_index(index_name)
        while index_name in [idx.name for idx in pc.list_indexes()]:
             print("Waiting for deletion...")
             time.sleep(2)
        print("Index deleted. It will be recreated with the correct 'dotproduct' metric the next time you run the backend.")
    else:
        print(f"Index {index_name} does not exist. Nothing to delete.")

if __name__ == "__main__":
    reset_db()
