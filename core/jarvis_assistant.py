import os
import time
import json
import threading
import subprocess
import cv2
import pyautogui
import pyttsx3
from cvzone.HandTrackingModule import HandDetector
from dotenv import load_dotenv
import speech_recognition as sr
import google.generativeai as genai
import webbrowser
import pygetwindow as gw
import urllib.parse

# ------------ Configurações iniciais ------------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("❌ Erro: Chave da API GEMINI_API_KEY não encontrada. Verifique seu arquivo .env")
    exit(1)

CACHE_FILE = "command_cache.json"
# MODEL_NAME = "gemini-1.5-pro" # Modelo mais recente e capaz
MODEL_NAME = "gemini-1.0-pro" # Usando um modelo mais comum para evitar problemas de disponibilidade imediata, ajuste se necessário.

genai.configure(api_key=API_KEY)
try:
    model = genai.GenerativeModel(MODEL_NAME)
    print(f"✅ Modelo Gemini '{MODEL_NAME}' carregado com sucesso.")
except Exception as e:
    print(f"❌ Erro ao carregar o modelo Gemini '{MODEL_NAME}': {e}")
    print("➡️ Verifique se o nome do modelo está correto e se você tem acesso a ele.")
    exit(1)


# Initialize TTS
try:
    tts = pyttsx3.init()
    print("✅ TTS (Text-to-Speech) inicializado.")
except Exception as e:
    print(f"❌ Erro ao inicializar TTS: {e}")
    tts = None # Define como None para que possamos checar antes de usar

# Speech recognizer
recognizer = sr.Recognizer()
print("✅ Reconhecedor de fala inicializado.")

# Gesture detector (max 1 mão)
try:
    detector = HandDetector(detectionCon=0.8, maxHands=1) # Aumentei um pouco a confiança de detecção
    print("✅ Detector de gestos inicializado.")
except Exception as e:
    print(f"❌ Erro ao inicializar HandDetector: {e}")
    exit(1)


# Load or init cache (não usado ativamente neste fluxo, mas mantido)
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)
else:
    cache = {}

# Debounce flag para gestos
gesture_listen = False
listen_lock = threading.Lock()

# ------------ Debug: inicializar webcam ------------
print("➡️ Tentando inicializar a webcam...")
cap = cv2.VideoCapture(0) # Tenta a webcam padrão
if not cap.isOpened():
    print("⚠️ Aviso: Não consegui acessar a webcam com índice 0. Tentando índice 1...")
    cap = cv2.VideoCapture(1) # Tenta a próxima webcam
    if not cap.isOpened():
        print("❌ Erro: Não consegui acessar nenhuma webcam (índices 0 e 1 testados).")
        print("➡️ Verifique se a webcam está conectada e não está sendo usada por outro programa.")
        exit(1)
print("✅ Webcam inicializada com sucesso.")


# ------------- Funções auxiliares -------------

def speak(text):
    if tts:
        print(f"[ASSISTENTE]: {text}")
        tts.say(text)
        tts.runAndWait()
    else:
        print(f"[ASSISTENTE - SEM VOZ]: {text}")

def execute_system_action(command_text):
    cmd = command_text.lower().strip()
    print(f"[DEBUG] Tentando executar ação local para: '{cmd}'")

    # Comando: "pesquise [termo] no youtube" ou "pesquisar [termo] no youtube"
    if ("pesquise" in cmd and "no youtube" in cmd) or ("pesquisar" in cmd and "no youtube" in cmd):
        query = cmd.replace("pesquise", "").replace("pesquisar", "").replace("no youtube", "").strip()
        if query:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            return f"Pesquisando '{query}' no YouTube."
        else:
            webbrowser.open("https://www.youtube.com")
            return "Abrindo YouTube. O que você gostaria de pesquisar?"

    # Comando: "pesquise [termo] no google" ou "pesquisar [termo] no google"
    elif ("pesquise" in cmd and "no google" in cmd) or ("pesquisar" in cmd and "no google" in cmd):
        query = cmd.replace("pesquise", "").replace("pesquisar", "").replace("no google", "").strip()
        if query:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(url)
            return f"Pesquisando '{query}' no Google."
        else:
            webbrowser.open("https://www.google.com")
            return "Abrindo Google. O que você gostaria de pesquisar?"

    # Comando: "minimize a minha tela" ou "minimizar janela"
    elif "minimize a minha tela" in cmd or "minimizar janela" in cmd:
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                active_window.minimize()
                return "Minimizando a janela atual."
            else:
                return "Não há janela ativa para minimizar."
        except Exception as e:
            print(f"Erro ao minimizar janela: {e}")
            return f"Erro ao tentar minimizar a janela: {e}"

    elif "youtube" in cmd: # Comando genérico para abrir YouTube
        webbrowser.open("https://www.youtube.com")
        return "Abrindo YouTube."
    elif "google" in cmd: # Comando genérico para abrir Google
        webbrowser.open("https://www.google.com")
        return "Abrindo Google."
    elif "bloco de notas" in cmd or "notepad" in cmd:
        try:
            subprocess.Popen(["notepad.exe"])
            return "Abrindo o Bloco de Notas."
        except Exception as e:
            print(f"Erro ao abrir Bloco de Notas: {e}")
            return f"Falha ao abrir o Bloco de Notas: {e}"
    elif "fechar janela" in cmd:
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                active_window.close()
                return "Fechando a janela atual."
            else:
                return "Não há janela ativa para fechar."
        except Exception as e:
            print(f"Erro ao fechar janela: {e}")
            return f"Erro ao fechar a janela: {e}"
    elif "maximizar janela" in cmd or "restaurar janela" in cmd:
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                if active_window.isMinimized:
                    active_window.restore()
                    return "Restaurando a janela."
                elif active_window.isMaximized:
                    active_window.restore() # Se já estiver maximizada, restaura para o tamanho normal
                    return "Restaurando a janela para o tamanho normal."
                else:
                    active_window.maximize()
                    return "Maximizando a janela atual."
            else:
                return "Não há janela ativa para maximizar ou restaurar."
        except Exception as e:
            print(f"Erro ao maximizar/restaurar janela: {e}")
            return f"Erro ao maximizar ou restaurar a janela: {e}"
    elif "pressionar tecla" in cmd: # Ex: "pressionar tecla enter"
        key_to_press = cmd.replace("pressionar tecla", "").strip()
        if key_to_press:
            try:
                pyautogui.press(key_to_press)
                return f"Pressionando a tecla '{key_to_press}'."
            except Exception as e:
                print(f"Erro ao pressionar tecla '{key_to_press}': {e}")
                return f"Não consegui pressionar a tecla '{key_to_press}'. Verifique o nome da tecla."
        else:
            return "Qual tecla você gostaria que eu pressionasse?"
    # Adicione mais ações diretas aqui para melhor performance

    return None  # Indica que nenhuma ação local foi encontrada para o comando direto

def listen_command(duration=5):
    with sr.Microphone() as source:
        print("[MICROFONE] Ajustando para ruído ambiente...")
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            print(f"⚠️ Aviso: Falha ao ajustar para ruído ambiente: {e}")
        print(f"[MICROFONE] Ouvindo por {duration} segundos...")
        try:
            audio = recognizer.listen(source, phrase_time_limit=duration, timeout=duration + 2) # Adicionado timeout
        except sr.WaitTimeoutError:
            print("[MICROFONE] Nenhum áudio detectado (timeout).")
            return None
        except Exception as e:
            print(f"❌ Erro durante a escuta: {e}")
            return None

    try:
        print("[MICROFONE] Reconhecendo fala...")
        text = recognizer.recognize_google(audio, language="pt-BR")
        print(f"[USUÁRIO DISSE]: '{text}'")
        return text
    except sr.UnknownValueError:
        print("[MICROFONE] Não entendi o áudio.")
        speak("Desculpe, não consegui entender o que você disse.")
        return None
    except sr.RequestError as e:
        print(f"❌ Erro no serviço de reconhecimento de fala do Google: {e}")
        speak("Desculpe, estou com problemas para acessar o serviço de reconhecimento de voz.")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado no reconhecimento de fala: {e}")
        speak("Ocorreu um erro inesperado ao tentar processar sua voz.")
        return None

def interpret_with_gemini(command_text):
    if not API_KEY: # Checagem extra
        return "A chave da API do Gemini não está configurada. Não posso processar este comando."

    prompt_instructions = (
        "Você é Jarvis, um assistente pessoal prestativo e conciso. "
        "Seu objetivo é interpretar o comando do usuário e, se for uma ação que você pode executar diretamente, "
        "responda APENAS com 'execute: <ação detalhada>'. Não adicione frases como 'Ok, vou executar'. "
        "As ações diretas que você pode pedir são:\n"
        "- 'abrir youtube'\n"
        "- 'abrir google'\n"
        "- 'abrir bloco de notas'\n"
        "- 'fechar janela'\n"
        "- 'minimizar janela'\n"
        "- 'maximizar janela'\n"
        "- 'restaurar janela'\n"
        "- 'pesquisar no google <termo da pesquisa>'\n"
        "- 'pesquisar no youtube <termo da pesquisa>'\n"
        "- 'pressionar tecla <nome da tecla>'\n"
        "Se o comando não for uma dessas ações ou for uma pergunta, responda normalmente como um assistente. "
        "Exemplo de comando do usuário: 'Jarvis, pesquise como fazer bolo no Google'\n"
        "Sua resposta esperada: 'execute: pesquisar no google como fazer bolo'\n"
        "Exemplo de comando do usuário: 'Olá Jarvis, como você está?'\n"
        "Sua resposta esperada: 'Estou funcionando perfeitamente! Como posso ajudar?'\n"
        "Comando do usuário atual: "
    )
    full_prompt = prompt_instructions + command_text
    print(f"[GEMINI] Enviando prompt: '{command_text}'") # Mostra apenas o comando do usuário no log

    try:
        # Geração de conteúdo com o modelo Gemini
        response = model.generate_content(full_prompt)

        # Verifica se há partes na resposta e se a primeira parte tem texto
        if response.parts:
            response_text = "".join(part.text for part in response.parts if hasattr(part, 'text')).strip()
        elif hasattr(response, 'text') and response.text: # Fallback para modelos mais antigos ou respostas simples
             response_text = response.text.strip()
        else: # Se não houver texto de forma alguma
            print("[GEMINI] Resposta sem conteúdo de texto.")
            # Tenta acessar candidates se parts estiver vazio, como um último recurso
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                 response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')).strip()
            else:
                return "Desculpe, não obtive uma resposta válida do modelo de linguagem."


        print(f"[GEMINI] Resposta recebida: '{response_text}'")

        if response_text.lower().startswith("execute:"):
            action_command = response_text[len("execute:"):].strip()
            print(f"[GEMINI] Pediu para executar: '{action_command}'")
            # Tenta executar a ação. Se execute_system_action retornar uma mensagem (sucesso ou erro),
            # essa mensagem será falada. Se retornar None (ação não reconhecida por Gemini),
            # então uma mensagem padrão de falha será usada.
            action_result = execute_system_action(action_command)
            if action_result:
                return action_result # Retorna a mensagem de sucesso/erro da execução
            else:
                return f"Tentei executar '{action_command}' via Gemini, mas não é uma ação conhecida."
        else:
            # Se não for um comando "execute:", é uma resposta conversacional
            return response_text

    except Exception as e:
        print(f"❌ Erro ao chamar API Gemini ou processar resposta: {e}")
        return "Desculpe, ocorreu um erro ao tentar processar seu comando com o modelo de linguagem."

# ----------- Loop principal -----------
print("➡️ Entrando no loop principal. Pressione 'q' na janela da webcam para sair.")
speak("Assistente Jarvis iniciado. Faça o gesto para me ativar.")

try:
    while True:
        success, frame = cap.read()
        if not success:
            print("❌ Falha ao capturar frame da webcam. Verifique a conexão.")
            time.sleep(1) # Pausa antes de tentar novamente
            # Tenta reabrir a câmera se falhar continuamente
            cap.release()
            cap = cv2.VideoCapture(0) # ou o índice que funcionou
            if not cap.isOpened():
                speak("Perdi a conexão com a webcam e não consegui reconectar. Encerrando.")
                break # Sai do loop se não conseguir reabrir
            else:
                speak("Webcam reconectada.")
            continue


        frame = cv2.flip(frame, 1) # Espelha a imagem
        hands, processed_frame = detector.findHands(frame.copy()) # Usa uma cópia para desenhar

        if hands:
            hand = hands[0] # Pega a primeira mão detectada
            fingers_up = detector.fingersUp(hand)
            # print(f"[DEBUG] Dedos levantados: {fingers_up}") # Log para depuração do gesto

            # Gesto: Indicador e médio levantados (Paz e amor / V de vitória)
            if fingers_up == [0, 1, 1, 0, 0]:
                if not gesture_listen: # Só ativa se não estiver ouvindo
                    with listen_lock: # Garante que a lógica de escuta não execute múltiplas vezes
                        gesture_listen = True # Define a flag para evitar reativação imediata

                    speak("Estou ouvindo.")
                    print("--- Gesto detectado ---")
                    command_recognized = listen_command(duration=5) # Escuta por 5 segundos

                    if command_recognized:
                        speak(f"Você disse: {command_recognized}. Processando...")
                        # 1. Tenta executar diretamente
                        action_feedback = execute_system_action(command_recognized)

                        # 2. Se não foi uma ação direta, tenta com Gemini
                        if not action_feedback:
                            print(f"[INFO] Comando '{command_recognized}' não é uma ação local direta. Consultando Gemini...")
                            action_feedback = interpret_with_gemini(command_recognized)

                        # 3. Feedback final
                        if action_feedback:
                            speak(action_feedback)
                        else:
                            # Se nem a execução direta nem o Gemini retornaram algo útil
                            speak("Desculpe, não consegui entender ou executar esse comando.")
                    else:
                        # listen_command já deve ter falado que não entendeu
                        pass # speak("Não recebi nenhum comando claro.") # Ou uma mensagem aqui se preferir

                    # Pausa após o processamento do comando para evitar reativação imediata pelo mesmo gesto
                    print("--- Fim do processamento do comando ---")
                    time.sleep(2) # Aguarda 2 segundos antes de permitir novo gesto
                    with listen_lock:
                        gesture_listen = False # Libera para o próximo gesto

        cv2.imshow("Jarvis Assistant - Webcam Feed", processed_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            speak("Encerrando o assistente Jarvis.")
            break
        elif key == ord('t'): # Tecla 't' para testar o TTS
            print("[TESTE] Testando a fala.")
            speak("Olá! Este é um teste de som.")

finally:
    print("➡️ Liberando recursos...")
    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
    if tts:
        # Garante que a engine TTS seja limpa corretamente em algumas plataformas
        # Pode ser necessário um loop para processar eventos pendentes antes de parar
        try:
            tts.stop()
        except Exception as e:
            print(f"Erro ao parar TTS: {e}")
    print("✅ Recursos liberados. Programa encerrado.")