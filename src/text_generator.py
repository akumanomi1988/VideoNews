from transformers import GPT2LMHeadModel, GPT2Tokenizer

def generate_text_with_huggingface(trends):
    model_name = "mrm8488/spanish-gpt2"
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    
    prompt = f"Escribe un texto descriptivo sobre las siguientes tendencias de Twitter: {', '.join(trends)}"
    input_ids = tokenizer.encode(prompt, return_tensors='pt')
    output = model.generate(input_ids, max_length=150, num_return_sequences=1)
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    return generated_text
