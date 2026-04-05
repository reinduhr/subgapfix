from typing import List, Dict
import typer
import ollama

def polish_with_llm(
        segments: List[Dict], 
        temperature: float = 0.0,
        model = 'llama3.1:8b-instruct-q5_K_M') -> List[Dict]:
    """
    Use an LLM to polish WhisperX sentences into natural, clean text.
    """
    polished = []
    
    for seg in segments:
        original_text = seg.get("text", "").strip()
        if not original_text:
            polished.append(seg)
            continue

        prompt = f"""   You are an expert editor for spoken transcripts.
                        Improve the following text:
                        - Fix grammar and awkward phrasing
                        - Remove repetitions and filler words
                        - Make it natural and fluent
                        - Keep the original meaning exactly
                        - Do NOT add or remove information
                        - Return ONLY the cleaned sentence, nothing else.

                        Text: {original_text}

                        Cleaned version:"""

        try:
            response = ollama.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt.strip()}],
                options={'temperature': temperature, 'num_ctx': 8192}
            )
            cleaned_text = response['message']['content'].strip()
            
            new_seg = seg.copy()
            new_seg["text"] = cleaned_text
            polished.append(new_seg)
            
        except Exception as e:
            typer.echo(f"Warning: {response.model} failed on a segment: {e}")
            polished.append(seg)  # fallback to original

    typer.echo(f"✅ {response.model} polished {len(polished)} segments")
    return polished