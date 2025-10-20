# Citation Verification Test
# Test if our URL extraction is working correctly

import re
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load API key
load_dotenv("key.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_urls(text):
    """Extract URLs from text."""
    return re.findall(r'https?://[^\s)>\]]+', text)

def test_citation_detection():
    """Test our citation detection with known prompts."""
    
    test_prompts = [
        "What are the best programming resources online? Include URLs.",
        "Find me some Reddit discussions about AI. Provide links.",
        "Show me Wikipedia articles about climate change with URLs.",
        "What are the top tech news sites? Include website links."
    ]
    
    print("Testing citation detection...")
    
    for i, prompt in enumerate(test_prompts, 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                messages=[
                    {"role": "system", "content": "You are an assistant that provides helpful information and cites sources with full URLs when relevant."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            urls = extract_urls(content)
            
            print(f"\nTest {i}: {prompt}")
            print(f"Response length: {len(content)} characters")
            print(f"URLs found: {len(urls)}")
            for url in urls[:3]:  # Show first 3 URLs
                print(f"  - {url}")
            if len(urls) > 3:
                print(f"  ... and {len(urls)-3} more")
                
        except Exception as e:
            print(f"Error in test {i}: {e}")
    
    print("\nCitation detection test complete!")

if __name__ == "__main__":
    test_citation_detection()
