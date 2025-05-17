import cv2
import time
import pyautogui
from cvzone.HandTrackingModule import HandDetector
import webbrowser

# Inicializa webcam e detector
cap = cv2.VideoCapture(0)
detector = HandDetector(detectionCon=0.8, maxHands=1)

# Debounce: tempo mínimo, em segundos, entre execuções do mesmo gesto
DEBOUNCE = {
    "Punho fechado": 2.0,
    "Indicador":      2.0,
    "tres dedos":     2.0,
    "rock": 5.0,
    "Dois dedos":     0.0,
    "Mao aberta":     0.0,
    "tres ultimos": 5.0,
    "dog": 5.0,
}

# Armazena o timestamp da última execução de cada gesto
last_action_time = {g: 0.0 for g in DEBOUNCE.keys()}

def reconhecer_gestos(dedos):
    if dedos == [0,0,0,0,0]:
        return "Punho fechado"
    if dedos == [1,1,0,0,1]:
        return "rock"
    if dedos == [0,1,1,1,0]:
        return "tres dedos"
    if dedos == [1,1,1,1,1]:
        return "Mao aberta"
    if dedos == [0,1,0,0,0]:
        return "Indicador"
    if dedos == [0,1,1,0,0]:
        return "Dois dedos"
    if dedos == [0,0,1,1,1]:
        return "tres ultimos"
    if dedos == [0,1,0,1,1]:
        return "dog"
    
    return "Gesto desconhecido"

def executar_acao(gesto):
    now = time.time()
    debounce_time = DEBOUNCE.get(gesto, 0.0)
    last = last_action_time.get(gesto, 0.0)

    # Se não passou o debounce, sai
    if now - last < debounce_time:
        return

    # Atualiza o último timestamp
    last_action_time[gesto] = now

    # Mapeia o gesto para uma ação
    if gesto == "Punho fechado":
        pyautogui.press("playpause")

    elif gesto == "Indicador":
        pyautogui.press("right")

    elif gesto == "tres dedos":
        pyautogui.press("left")

    elif gesto == "rock":
        webbrowser.open_new_tab("https://www.google.com")

    elif gesto == "Dois dedos":
        pyautogui.press("volumeup")

    elif gesto == "Mao aberta":
        pyautogui.press("volumedown")

    elif gesto == "tres ultimos":
        webbrowser.open_new_tab("https://www.youtube.com/")
    
    elif gesto == "dog":
        pyautogui.hotkey("alt", "space")  
        time.sleep(0.2)                   
        pyautogui.press("n")  

# Loop principal
while True:
    success, img = cap.read()
    if not success:
        break

    img = cv2.flip(img, 1)
    hands, img = detector.findHands(img)

    if hands:
        hand = hands[0]
        dedos = detector.fingersUp(hand)
        gesto = reconhecer_gestos(dedos)

        # Sobrepõe o nome do gesto
        cv2.putText(img, gesto, (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (225, 0, 225), 3)
        executar_acao(gesto)

    # Exibe o stream
    cv2.imshow("Gesture Recognition", img)

    # Sai se apertar 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
