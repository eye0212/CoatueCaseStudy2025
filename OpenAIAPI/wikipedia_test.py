# Wikipedia Citation Test
# Test specific prompts that should trigger Wikipedia citations

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

def test_wikipedia_citations():
    """Test prompts specifically designed to trigger Wikipedia citations."""
    
    # Prompts that should logically trigger Wikipedia citations
    wikipedia_test_prompts = [
        "What is the history of World War II? Include Wikipedia links.",
        "Explain the scientific method. Provide Wikipedia sources.",
        "Tell me about the periodic table. Include Wikipedia URLs.",
        "What is photosynthesis? Cite Wikipedia articles.",
        "Explain quantum mechanics. Provide Wikipedia links.",
        "Tell me about ancient Rome. Include Wikipedia sources.",
        "What is climate change? Cite Wikipedia articles.",
        "Explain machine learning basics. Provide Wikipedia URLs.",
        "Tell me about the solar system. Include Wikipedia links.",
        "What is democracy? Cite Wikipedia sources."
    ]
    
    print("Testing Wikipedia citation patterns...")
    print("=" * 50)
    
    total_urls = 0
    wikipedia_urls = 0
    
    for i, prompt in enumerate(wikipedia_test_prompts, 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides accurate information and cites reliable sources including Wikipedia when appropriate."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            urls = extract_urls(content)
            
            # Count Wikipedia URLs
            wiki_urls = [url for url in urls if 'wikipedia' in url.lower()]
            
            total_urls += len(urls)
            wikipedia_urls += len(wiki_urls)
            
            print(f"\nTest {i}: {prompt}")
            print(f"Total URLs: {len(urls)}")
            print(f"Wikipedia URLs: {len(wiki_urls)}")
            
            if wiki_urls:
                for url in wiki_urls:
                    print(f"  ✓ {url}")
            else:
                print("  ✗ No Wikipedia URLs found")
                
            # Show first few URLs to see what was cited instead
            if urls and not wiki_urls:
                print("  Other URLs cited:")
                for url in urls[:3]:
                    print(f"    - {url}")
                if len(urls) > 3:
                    print(f"    ... and {len(urls)-3} more")
                    
        except Exception as e:
            print(f"Error in test {i}: {e}")
    
    print("\n" + "=" * 50)
    print(f"SUMMARY:")
    print(f"Total URLs found: {total_urls}")
    print(f"Wikipedia URLs: {wikipedia_urls}")
    print(f"Wikipedia percentage: {(wikipedia_urls/total_urls*100):.1f}%" if total_urls > 0 else "No URLs found")

if __name__ == "__main__":
    test_wikipedia_citations()
