from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
import requests
import sys
import time
from colorama import Fore, Style
import json
import asyncio
from ollama import AsyncClient

def get_chosen_model(models):
    while True:
        chosen_model_index = input(Fore.CYAN + "Enter the index of the chosen model: " + Style.RESET_ALL)
        if chosen_model_index.isdigit():
            chosen_model_index = int(chosen_model_index) - 1
            if 0 <= chosen_model_index < len(models):
                chosen_model = models[chosen_model_index]['name']
                print(Fore.YELLOW + f"[*] Using Model {chosen_model}" + Style.RESET_ALL)
                return chosen_model
            else:
                print(Fore.RED + f"Invalid index {chosen_model_index}. Please enter a valid index." + Style.RESET_ALL)
        else:
            print(Fore.RED + f"Invalid index {chosen_model_index}. Please enter a valid index." + Style.RESET_ALL)

def print_model_info(server, part):
    print(Fore.YELLOW + 'Server: ' + server + Style.RESET_ALL)
    for key, value in part.items():
        print(Fore.YELLOW + f'{key.capitalize()}: {value}' + Style.RESET_ALL)

def chat_with_ollama(server, model, query):
    async def chat():
        message = {'role': 'user', 'content': query}
        async for part in await AsyncClient(host=server).chat(model=model, messages=[message], stream=True):
            try:
                if part.get('done', False):
                    print('DONE')
                    return
                else:
                    print(Fore.GREEN + part['message']['content'] + Style.RESET_ALL, end='', flush=True)
            except (KeyError, Exception) as e:
                print(Fore.RED + f'Error: {e}' + Style.RESET_ALL)
                break

    asyncio.run(chat())

def main():
    with open('config.json', 'r') as file:
        config = json.load(file)

    history = FileHistory('prompt_history.txt')

    arg0 = sys.argv[1] if len(sys.argv) > 1 else None
    api_loc = arg0 if arg0 else config.get('API_URL', '')

    while True:
        try:
            response = requests.get(f'http://{api_loc}:11434/')
            if response.text == "Ollama is running":
                print(Fore.GREEN + f"[!] CONNECTED : Ollama API is running @ {api_loc}" + Style.RESET_ALL)
                response = requests.get(f'http://{api_loc}:11434/api/tags')
                decoded_response = response.json()
                models = decoded_response.get('models', [])
                print(Fore.YELLOW + "Available Models:" + Style.RESET_ALL)
                for i, model in enumerate(models, 1):
                    print(Fore.RED + f"{i}. {model['name']}" + Style.RESET_ALL)

                chosen_model = get_chosen_model(models)
                break
            else:
                print(Fore.RED + "Ollama API is not running. Retrying..." + Style.RESET_ALL)
                time.sleep(5)

        except (requests.exceptions.RequestException, Exception) as e:
            print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
            print()
            print(Fore.RED + "Ollama API is not running. Run 'ollama serve &'..." + Style.RESET_ALL)
            return

    while True:
        prompt_text = "\n>> "
        system_prompt = f"You are an advanced AI based on {chosen_model}, act as a dev assistant, be explicit."
        user_prompt = prompt(prompt_text, history=history)
        final_prompt = system_prompt + user_prompt
        if not user_prompt:
            print(Fore.RED + "[!] Empty prompt" + Style.RESET_ALL)
            continue

        print(Fore.YELLOW + f"[User] {user_prompt}" + Style.RESET_ALL)

        if not chosen_model:
            print(Fore.RED + "Chosen model is empty or null. Do you want to install mistral:7b ?" + Style.RESET_ALL)
            continue

        init_time = time.time()
        server = api_loc
        query = user_prompt
        model = chosen_model

        try:
            chat_with_ollama(server, model, query)
        except asyncio.exceptions.CancelledError:
            print(Fore.RED + "Error: Chat with Ollama was cancelled." + Style.RESET_ALL)

        response_time = round(time.time() - init_time, 2)
        print(f"\nResponseTime = {response_time}")
        time.sleep(0.25)  # AVOID BAD LOOPING

if __name__ == "__main__":
    main()
