"""Gemini Service for AI Exam Paper Generator.

Handles communication with Google Gemini API using the official google-genai SDK,
ensuring structured JSON output generation and robust fallback parsing.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError, ClientError, ServerError
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    APIError = Exception
    ClientError = Exception
    ServerError = Exception
    GENAI_AVAILABLE = False


class GeminiService:
    """Service wrapper for Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
        self._client: Optional[Any] = None

    def get_client(self) -> Any:
        """Initializes and returns the official genai Client."""
        if not GENAI_AVAILABLE:
            raise RuntimeError(
                "The 'google-genai' library is not installed. Please run: pip install google-genai"
            )
        
        # Read freshest key if not provided initially
        current_key = self.api_key or os.getenv("GEMINI_API_KEY", "").strip()
        if not current_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please supply a valid Gemini API key in your .env file or UI."
            )
        
        if self._client is None or self.api_key != current_key:
            self.api_key = current_key
            self._client = genai.Client(api_key=self.api_key)
            
        return self._client

    def clean_json_string(self, text: str) -> str:
        """Extracts and strips JSON payload from response text."""
        if not text:
            return ""
        
        cleaned = text.strip()
        
        # Strip ```json ... ``` or ``` ... ``` code fence
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Find the outer JSON boundaries if surrounding commentary exists
        start_brace = cleaned.find("{")
        end_brace = cleaned.rfind("}")
        if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
            cleaned = cleaned[start_brace : end_brace + 1]

        return cleaned

    @staticmethod
    def repair_json_escapes(s: str) -> str:
        """Repairs unescaped backslashes and invalid escape sequences inside JSON string literals."""
        res = []
        in_string = False
        i = 0
        n = len(s)

        while i < n:
            c = s[i]
            if not in_string:
                if c == '"':
                    in_string = True
                res.append(c)
                i += 1
            else:
                if c == '"':
                    in_string = False
                    res.append(c)
                    i += 1
                elif c == '\\':
                    if i + 1 < n:
                        next_c = s[i + 1]
                        # Valid standard JSON escape sequences
                        if next_c in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't']:
                            res.append(c)
                            res.append(next_c)
                            i += 2
                        elif next_c == 'u' and i + 5 < n and all(ch in '0123456789abcdefABCDEF' for ch in s[i+2:i+6]):
                            res.append(s[i:i+6])
                            i += 6
                        else:
                            # Invalid escape (e.g. \d, \s, \w, \e, \0, \alpha, etc.) -> double escape it
                            res.append('\\\\')
                            i += 1
                    else:
                        res.append('\\\\')
                        i += 1
                else:
                    res.append(c)
                    i += 1

        return "".join(res)

    def parse_json(self, text: str) -> Dict[str, Any]:
        """Parses JSON text with multiple fallback recovery strategies."""
        if not text:
            raise ValueError("Gemini returned an empty response.")

        # 1. Direct parse with strict=False (handles unescaped control chars like tabs/newlines)
        try:
            return json.loads(text, strict=False)
        except Exception:
            pass

        # 2. Repair invalid backslash escapes (e.g. \d, \s, LaTeX math \alpha, etc.)
        repaired = self.repair_json_escapes(text)
        try:
            return json.loads(repaired, strict=False)
        except Exception:
            pass

        # 3. Clean any trailing commas before closing braces or brackets
        cleaned_trailing = re.sub(r',\s*([}\]])', r'\1', repaired)
        try:
            return json.loads(cleaned_trailing, strict=False)
        except Exception:
            pass

        # Final attempt: let json.loads throw standard exception if unparseable
        return json.loads(text, strict=False)

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Sends prompt to Gemini and parses the structured JSON response,

        with automatic retry on 503/429 errors and fallback model resilience.
        """
        import time

        client = self.get_client()
        candidates = [self.model, "gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-3.6-flash"]
        candidate_models = []
        for m in candidates:
            if m and m not in candidate_models:
                candidate_models.append(m)

        last_error = None

        for model_candidate in candidate_models:
            config = types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json"
            )
            if system_instruction:
                config.system_instruction = system_instruction

            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=prompt,
                        config=config
                    )

                    raw_text = response.text or ""
                    cleaned = self.clean_json_string(raw_text)

                    parsed = self.parse_json(cleaned)
                    return parsed

                except ClientError as e:
                    err_msg = str(e)
                    if "404" in err_msg and "model" in err_msg.lower():
                        last_error = e
                        break  # try next candidate model
                    elif "403" in err_msg or "API_KEY_INVALID" in err_msg or "401" in err_msg:
                        raise RuntimeError(
                            "Invalid or unauthorized Gemini API key. Please check your GEMINI_API_KEY in .env."
                        ) from e
                    elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        last_error = e
                        break  # quota exhausted on this model, try next candidate model
                    raise RuntimeError(f"Gemini API Client Error: {err_msg}") from e

                except ServerError as e:
                    # 503 unavailable or high demand - if multiple attempts fail, break to next candidate model
                    last_error = e
                    if attempt >= 1:
                        break  # move to next model candidate
                    wait_sec = 1
                    time.sleep(wait_sec)
                    continue

                except (json.JSONDecodeError, ValueError) as e:
                    last_error = e
                    if attempt >= max_retries - 1:
                        break
                    time.sleep(1)
                    continue

                except Exception as e:
                    last_error = e
                    if "503" in str(e) or "unavailable" in str(e).lower():
                        if attempt >= 1:
                            break
                        wait_sec = 1
                        time.sleep(wait_sec)
                        continue
                    raise RuntimeError(f"Unexpected error calling Gemini API: {str(e)}") from e

        raise RuntimeError(f"Gemini generation failed after retries across candidate models: {str(last_error)}")


# Global singleton instance with lazy initialization
gemini_service = GeminiService()
