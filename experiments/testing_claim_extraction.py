import os
from google import genai
from google.genai import types
from src.utils.loader_googlefile import load_video_file_from_metadata
from langchain_core.runnables import RunnableLambda
import asyncio

import time

def analyze_with_prompt(video_file, prompt_text):
    """
    Analyze video with a specific prompt
    
    Args:
        video_file: Uploaded video file object
        prompt_text: Analysis prompt
        
    Returns:
        Analysis result
    """
    client = genai.Client()
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_uri(
                file_uri=video_file.uri, 
                mime_type=video_file.mime_type
            ),
            prompt_text
        ]
    )
    return response.text

async def analyze_video_sequential(video_file, first_prompt, second_prompt_template):
    """
    Upload video, get first analysis, then use result in second analysis using LangChain
    
    Args:
        video_path: Path to the video file
        first_prompt: Prompt for initial analysis (e.g., summarization)
        second_prompt_template: Template for second prompt with {summary} placeholder
        
    Returns:
        Dictionary with both results
    """
    
    # Step 2: Create first runnable for summarization
    def run_first_analysis(input_data):
        print("\n--- Running First Analysis (Summarization) ---")
        result = analyze_with_prompt(video_file, first_prompt)
        return {"summary": result, "video_file": video_file}
    
    first_runnable = RunnableLambda(run_first_analysis)
    
    # Step 3: Create second runnable that uses the summary
    def run_second_analysis(input_data):
        print("\n--- Running Second Analysis (Using Summary) ---")
        summary = input_data["summary"]
        video_file = input_data["video_file"]
        
        # Format the second prompt with the summary
        formatted_prompt = second_prompt_template.format(summary=summary)
        
        result = analyze_with_prompt(video_file, formatted_prompt)
        return {"summary": summary, "claim": result}
    
    second_runnable = RunnableLambda(run_second_analysis)
    
    # Step 4: Chain them together
    chain = first_runnable | second_runnable
    
    # Step 5: Execute the chain
    results = await chain.ainvoke({})
    
    return results

# Synchronous wrapper
def analyze_video_sequential_sync(video_path, first_prompt, second_prompt_template):
    """
    Synchronous version of sequential video analysis
    """
    return asyncio.run(analyze_video_sequential(video_path, first_prompt, second_prompt_template))

if __name__ == "__main__":
    video = load_video_file_from_metadata("video_metadata.json")


    summarization_prompt = """
        Por favor faça uma extração abrangente deste vídeo incluindo:
        - Principais tópicos discutidos
        - Participantes do vídeo e tom do discurso
        """

    claim_prompt = """
        Com base no seguinte resumo do vídeo, gere em uma sentença a mensagme do vídeo
        """

    results = analyze_video_sequential_sync(
        video,
        summarization_prompt,
        claim_prompt
    )

    print(results)
