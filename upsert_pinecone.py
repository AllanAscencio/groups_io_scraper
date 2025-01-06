import os
import pandas as pd
import time
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from typing import List, Dict
import tiktoken

load_dotenv()

class PostsProcessor:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index("endo")
        self.tokenizer = tiktoken.encoding_for_model("text-embedding-3-large")

    def load_posts(self, csv_path: str) -> pd.DataFrame:
        """Load and filter posts with reply count > 0"""
        df = pd.read_csv(csv_path)
        return df[df['reply_count'] > 0]

    def truncate_text(self, text: str, max_tokens: int = 8000) -> str:
        """Truncate text to max tokens"""
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self.tokenizer.decode(tokens[:max_tokens])

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using text-embedding-3-large"""
        truncated_text = self.truncate_text(text)
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=truncated_text
        )
        return response.data[0].embedding

    def store_post_embedding(self, row: pd.Series, embedding: List[float]):
        """Store post embedding and metadata in Pinecone"""
        metadata = {
            "url": row['url'],
            "start_date": row['start_date'],
            "post_id": str(row['post_id']),
            "title": row['title'][:500]  # Limiting title length for safety
        }
        
        self.index.upsert(vectors=[{
            "id": str(row['post_id']),
            "values": embedding,
            "metadata": metadata
        }])

    def process_posts(self, csv_path: str):
        """Process all posts and store in Pinecone"""
        df = self.load_posts(csv_path)
        total_posts = len(df)
        print(f"Found {total_posts} posts with replies to process")

        for idx, row in df.iterrows():
            try:
                if pd.isna(row['full_content']):
                    print(f"Skipping post {row['post_id']}: No content")
                    continue
                    
                embedding = self.generate_embedding(row['full_content'])
                self.store_post_embedding(row, embedding)
                print(f"Processed post {row['post_id']} ({idx + 1}/{total_posts})")
                
                # Rate limiting
                time.sleep(0.5)
            except Exception as e:
                print(f"Error processing post {row['post_id']}: {str(e)}")

if __name__ == "__main__":
    processor = PostsProcessor()
    processor.process_posts("posts.csv")