import os
import sys

# Configuration
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen3-1.7B")
LLM_DEVICE = os.getenv("LLM_DEVICE", "cpu")  # 'cpu' or 'cuda'
LLM_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "512"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

_model = None
_tokenizer = None


def _get_local_model():
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            # Set device
            device = torch.device(LLM_DEVICE if torch.cuda.is_available() and LLM_DEVICE == "cuda" else "cpu")

            # Load tokenizer
            try:
                print(f"Loading tokenizer for {LLM_MODEL_NAME}...")
                _tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, local_files_only=True)
            except Exception as e:
                print(f"Failed to load tokenizer locally: {e}")
                if input("Do you want to download the tokenizer? [Y/n]").lower().strip() in ("yes", "y"):
                    _tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
                else:
                    print("Exiting...")
                    sys.exit(0)

            # Load model
            try:
                print(f"Loading model {LLM_MODEL_NAME} on {device}...")
                _model = AutoModelForCausalLM.from_pretrained(
                    LLM_MODEL_NAME,
                    local_files_only=True,
                    torch_dtype=torch.float32 if device.type == "cpu" else torch.float16,
                    device_map="auto" if device.type == "cuda" else None,
                ).to(device)
            except Exception as e:
                print(f"Failed to load model locally: {e}")
                if input("Do you want to download the model? [Y/n]").lower().strip() in ("yes", "y"):
                    _model = AutoModelForCausalLM.from_pretrained(
                        LLM_MODEL_NAME,
                        torch_dtype=torch.float32 if device.type == "cpu" else torch.float16,
                        device_map="auto" if device.type == "cuda" else None,
                    ).to(device)
                else:
                    print("Exiting...")
                    sys.exit(0)

        except ImportError as e:
            print(f"Required libraries not installed: {e}")
            _model = None
            _tokenizer = None
    return _model, _tokenizer


def generate_response(prompt: str, system_message: str = "You are a helpful music expert assistant.") -> str:
    """Generate a response using the local LLM.

    Args:
        prompt: The user prompt
        system_message: The system message for the model

    Returns:
        The generated response text

    Raises:
        RuntimeError: If generation fails
    """
    if USE_LOCAL_LLM:
        try:
            model, tokenizer = _get_local_model()
            if model and tokenizer:
                import torch

                # Format the input with system message
                if tokenizer.chat_template:
                    messages = [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                else:
                    input_text = f"{system_message}\n\nUser: {prompt}\n\nAssistant:"

                # Tokenize
                inputs = tokenizer(input_text, return_tensors="pt")
                if LLM_DEVICE == "cuda" and torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}

                # Generate
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=LLM_MAX_NEW_TOKENS,
                        temperature=LLM_TEMPERATURE,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id,
                    )

                # Decode
                generated_text = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
                return generated_text.strip()
            else:
                raise RuntimeError("Local model not available.")
        except Exception as e:
            raise RuntimeError(f"Local LLM generation failed: {e}")

    # Fallback to API if needed, but since we're implementing local, raise error
    raise RuntimeError("Local LLM is disabled and no API fallback implemented.")