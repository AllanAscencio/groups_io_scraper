import os
from dotenv import load_dotenv
import anthropic
from pinecone import Pinecone
import tiktoken
from typing import List, Dict
import pandas as pd
from datetime import datetime
from openai import OpenAI

load_dotenv()

class ForumSearcher:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index("endo")
        self.tokenizer = tiktoken.encoding_for_model("text-embedding-3-large")
        
        # Initialize dataframes
        self.posts_df = pd.read_csv('posts.csv')
        self.replies_df = pd.read_csv('replies.csv')
        
        # Convert IDs to string for consistent comparison
        self.posts_df['post_id'] = self.posts_df['post_id'].astype(str)
        self.replies_df['parent_post_id'] = self.replies_df['parent_post_id'].astype(str)

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

    def find_similar_posts(self, query: str, top_k: int = 5, threshold: float = 0.5) -> List[Dict]:
        """Find similar posts using vector similarity"""
        # Generate embedding for the query
        embedding = self.generate_embedding(query)

        # Query Pinecone
        query_response = self.index.query(
            vector=embedding,
            top_k=top_k,
            include_values=False,
            include_metadata=True
        )

        # Filter by threshold and extract results
        similar_posts = []
        for match in query_response.matches:
            if match.score >= threshold:
                similar_posts.append({
                    "post_id": match.metadata.get("post_id"),
                    "score": match.score,
                    "url": match.metadata.get("url"),
                    "title": match.metadata.get("title")
                })
        
        return similar_posts

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to consistent format"""
        try:
            date_obj = datetime.strptime(date_str, "%b %d, %Y %I:%M%p")
            return date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return date_str

    def build_conversation(self, post_id: str) -> Dict:
        """Build a conversation from a post ID"""
        # Get the main post
        post = self.posts_df[self.posts_df['post_id'] == post_id].iloc[0]
        
        # Get replies for this post
        replies = self.replies_df[self.replies_df['parent_post_id'] == post_id].copy()
        
        # Sort replies by date
        if not replies.empty:
            replies['parsed_date'] = replies['reply_date'].apply(self._parse_date)
            replies = replies.sort_values('parsed_date')

        # Build conversation structure
        conversation = {
            'title': post['title'],
            'url': post['url'],
            'post_id': post_id,
            'messages': [
                {
                    'type': 'original_post',
                    'author': post['author'],
                    'date': self._parse_date(post['date']),
                    'content': post['full_content']
                }
            ]
        }

        # Add replies
        for _, reply in replies.iterrows():
            conversation['messages'].append({
                'type': 'reply',
                'author': reply['reply_author'],
                'date': self._parse_date(reply['reply_date']),
                'content': reply['reply_content']
            })

        return conversation

    def format_conversations(self, similar_posts: List[Dict]) -> str:
        """Format conversations for similar posts"""
        formatted_output = []
        
        for post in similar_posts:
            conversation = self.build_conversation(post['post_id'])
            
            # Format conversation
            formatted_output.append(f"## Case {post['post_id']} (Similarity: {post['score']:.3f})")
            formatted_output.append(f"Title: {conversation['title']}")
            formatted_output.append(f"URL: {conversation['url']}\n")
            
            for msg in conversation['messages']:
                formatted_output.append(f"{msg['type'].replace('_', ' ').title()} by {msg['author']} on {msg['date']}:")
                formatted_output.append(f"{msg['content']}\n")
            
            formatted_output.append("---\n")
        
        return "\n".join(formatted_output)

class EndoRAG:
    def __init__(self):
        self.searcher = ForumSearcher()
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    def get_llm_response(self, question: str, similar_cases: str) -> tuple:
        """Get response from Claude"""
        prompt = """You are a pediatric endocrinologist tasked with answering a medical question. You will review similar cases or questions, summarize your findings, and outline next steps or procedures. If no suitable answer is found in the provided cases, you should respond based on your own knowledge as a pediatric endocrinologist, clearly indicating that it is your suggestion.

Here is the question you need to address:
<question>
{question}
</question>

Review the following similar cases or questions:
<similar_cases>
{cases}
</similar_cases>

Based on your review of the similar cases, please provide your response in the following format:

<response>
<summary_of_findings>
Summarize the key information and insights you've gathered from the similar cases that are relevant to the current question.
</summary_of_findings>

<next_steps>
Outline the recommended next steps or procedures based on your findings. If there are multiple possible approaches, list them in order of priority or likelihood of success.
</next_steps>

<additional_recommendations>
If the similar cases do not provide a satisfactory answer to the question, provide your own recommendations based on your knowledge as a pediatric endocrinologist. Clearly state that these are your suggestions and not derived from the provided cases.
</additional_recommendations>
</response>

Remember to maintain a professional and empathetic tone throughout your response, considering that you are addressing a medical question related to pediatric endocrinology. If you need any clarifications or if there are any contraindications or special considerations that should be noted, include them in your response."""

        # Format the prompt with actual content
        formatted_prompt = prompt.format(
            question=question,
            cases=similar_cases
        )

        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            temperature=0,
            system="You are a pediatric endocrinologist. Provide thorough, evidence-based responses while maintaining empathy and professionalism.",
            messages=[
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ]
        )
        return message.content, message.usage

    def process_query(self, question: str, top_k: int = 5, threshold: float = 0.5) -> tuple:
        """Process a query through the entire pipeline"""
        # Find similar posts
        similar_posts = self.searcher.find_similar_posts(
            query=question,
            top_k=top_k,
            threshold=threshold
        )
        
        # Format the conversations
        formatted_cases = self.searcher.format_conversations(similar_posts)
        
        # Get response from Claude
        response, usage = self.get_llm_response(question, formatted_cases)
        
        return response, usage, similar_posts

# Example usage
if __name__ == "__main__":
    rag = EndoRAG()
    
    question = """
    Please give me advice on how to treat a 9 yo male with non classic CAH and short stature. He is 120cm and 25kg. 
  
    """
    
    response, usage, similar_posts = rag.process_query(
        question=question,
        top_k=5,
        threshold=0.5
    )
    
    # Print results
    print("\n" + "="*50 + "\nSIMILAR POSTS FOUND:\n" + "="*50)
    for post in similar_posts:
        print(f"Post ID: {post['post_id']}, Score: {post['score']:.3f}")
        print(f"Title: {post['title']}")
        print(f"URL: {post['url']}\n")
    
    print("\n" + "="*50 + "\nCLAUDE'S RESPONSE:\n" + "="*50)
    print(response if isinstance(response, str) else response[0].text)
    
    # Calculate costs
    input_cost = usage.input_tokens * 0.00000375
    output_cost = usage.output_tokens * 0.000015
    total_cost = input_cost + output_cost
    
    print("\n" + "="*50 + "\nUSAGE STATS:\n" + "="*50)
    print(f"Total Cost: ${total_cost:.4f}")