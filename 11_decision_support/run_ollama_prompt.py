#!/usr/bin/env python3
from pathlib import Path
import argparse
import requests

DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_PROMPT_FILE = "11_decision_support/venue_prompt.md"
DEFAULT_OUTPUT_FILE = "11_decision_support/venue_shortlist.md"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT = 180


def list_installed_models(host: str, timeout: int) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]


def choose_model(requested_model: str, installed_models: list[str]) -> tuple[str, str | None]:
    if not installed_models:
        raise RuntimeError("No local Ollama models are installed. Run `ollama pull <model>` once.")

    if requested_model in installed_models:
        return requested_model, None

    # Prefer a llama model if available; otherwise use the first installed model.
    preferred = next((m for m in installed_models if m.startswith("llama")), installed_models[0])
    return preferred, requested_model


def extract_content(response_json: dict, endpoint: str) -> str:
    if endpoint == "/api/chat":
        return response_json["message"]["content"].strip()
    if endpoint == "/v1/chat/completions":
        return response_json["choices"][0]["message"]["content"].strip()
    if endpoint == "/api/generate":
        return response_json["response"].strip()
    raise ValueError(f"Unsupported endpoint parser: {endpoint}")


def call_model(host: str, model: str, prompt_text: str, timeout: int) -> tuple[str, str]:
    system_text = (
        "You are a structured data extractor and decision analyst. "
        "Follow the user's output format exactly."
    )

    endpoint_payloads = [
        (
            "/api/chat",
            {
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": prompt_text},
                ],
            },
        ),
        (
            "/v1/chat/completions",
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": prompt_text},
                ],
                "stream": False,
            },
        ),
        (
            "/api/generate",
            {
                "model": model,
                "stream": False,
                "prompt": f"{system_text}\n\n{prompt_text}",
            },
        ),
    ]

    errors = []
    for endpoint, payload in endpoint_payloads:
        url = f"{host.rstrip('/')}{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            errors.append(f"{endpoint}: request failed ({exc})")
            continue

        if response.status_code == 404:
            body_preview = response.text[:200].replace("\n", " ")
            errors.append(f"{endpoint}: 404 not found ({body_preview})")
            continue

        try:
            response.raise_for_status()
            data = response.json()
            return extract_content(data, endpoint), endpoint
        except Exception as exc:
            errors.append(f"{endpoint}: {exc}")

    error_text = "\n".join(errors)
    raise RuntimeError(f"All endpoint attempts failed:\n{error_text}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a prompt against local Ollama and write output to a file."
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--prompt-file",
        default=DEFAULT_PROMPT_FILE,
        help="Path to markdown/text file containing your full user prompt",
    )
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_FILE,
        help="Path to output markdown file for model response",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Ollama host URL (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    output_path = Path(args.output_file)

    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt_text:
        raise ValueError(f"Prompt file is empty: {prompt_path}")

    installed_models = list_installed_models(args.host, args.timeout)
    model_to_use, requested_but_missing = choose_model(args.model, installed_models)

    if requested_but_missing:
        print(
            f"Requested model '{requested_but_missing}' not installed. "
            f"Using '{model_to_use}' instead."
        )

    print(f"Model: {model_to_use}")
    print(f"Prompt file: {prompt_path}")
    print(f"Output file: {output_path}")

    content, endpoint_used = call_model(
        host=args.host,
        model=model_to_use,
        prompt_text=prompt_text,
        timeout=args.timeout,
    )

    output_path.write_text(content + "\n", encoding="utf-8")
    print(f"Endpoint used: {endpoint_used}")
    print(f"Wrote model output to: {output_path}")


if __name__ == "__main__":
    main()
