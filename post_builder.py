import pandas as pd
import json
from datetime import datetime
from typing import Optional

class ConversationBuilder:
    def __init__(self, posts_csv: str, replies_csv: str):
        """Initialize with paths to CSV files"""
        self.posts_df = pd.read_csv(posts_csv)
        self.replies_df = pd.read_csv(replies_csv)
        
        # Convert post_id to string in both dataframes
        self.posts_df['post_id'] = self.posts_df['post_id'].astype(str)
        if 'parent_post_id' in self.replies_df.columns:
            self.replies_df['parent_post_id'] = self.replies_df['parent_post_id'].astype(str)
        
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Convert date string to consistent format"""
        if not date_str or pd.isna(date_str):
            return None
        try:
            # Parse the date string and format it consistently
            date_obj = datetime.strptime(date_str, "%b %d, %Y %I:%M%p")
            return date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return date_str
    
    def list_available_posts(self) -> list:
        """List all available post IDs and titles"""
        return self.posts_df[['post_id', 'title']].to_dict('records')
    
    def get_conversation(self, post_id: str) -> dict:
        """Build a conversation from a post ID"""
        # Convert post_id to string for comparison
        post_id = str(post_id)
        
        # Get the main post
        matching_posts = self.posts_df[self.posts_df['post_id'] == post_id]
        if matching_posts.empty:
            print(f"No post found with ID: {post_id}")
            print("\nAvailable post IDs:")
            for post in self.list_available_posts()[:5]:  # Show first 5 posts
                print(f"- {post['post_id']}: {post['title']}")
            print("...")
            raise ValueError(f"Post ID {post_id} not found in the dataset")
        
        post = matching_posts.iloc[0]
        
        # Get all replies for this post
        replies = self.replies_df[self.replies_df['parent_post_id'] == post_id].copy()
        
        # Sort replies by date if available
        if not replies.empty and 'reply_date' in replies.columns:
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
    
    def save_conversation(self, post_id: str, output_file: str) -> None:
        """Get conversation and save to JSON file"""
        conversation = self.get_conversation(post_id)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)
        
        print(f"Conversation saved to {output_file}")
        
    def print_available_posts(self) -> None:
        """Print all available post IDs and titles"""
        print("\nAvailable Posts:")
        for post in self.list_available_posts():
            print(f"ID: {post['post_id']} - Title: {post['title']}")

# Example usage:
if __name__ == "__main__":
    builder = ConversationBuilder('posts.csv', 'replies.csv')
    
    # Print available posts first
    print("Available posts in the dataset:")
    builder.print_available_posts()
    
    # Example post ID
    post_id = "110019839"
    
    try:
        # Get conversation
        conversation = builder.get_conversation(post_id)
        
        # Save to file
        builder.save_conversation(post_id, f'conversation_{post_id}.json')
        
        # Print preview
        print("\nConversation Preview:")
        print(f"Title: {conversation['title']}")
        print(f"Total messages: {len(conversation['messages'])}")
        print("\nFirst message preview:")
        print(f"Author: {conversation['messages'][0]['author']}")
        print(f"Content: {conversation['messages'][0]['content'][:200]}...")
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")