import cv2
from cvzone.HandTrackingModule import HandDetector

#inicia a captura de vídeo da webcam 
cap = cv2.VideoCapture(0)

#inicia o detector de mão

detector = HandDetector(detectionCon=0.8, maxHands=2)

while True:
    #captura o frame da webcam
    success, img = cap.read()

    #espelha a imagem
    img = cv2.flip(img,1)

    #detecta a mão e retorna imagem modificada e dados da mão
    hands, img = detector.findHands(img)

    #mostrar a mão detectada
    if hands:
         for hand in hands:
            lmList = hand["lmList"] #lista com as posições dos 21 pontos (landmarks)
            bbox = hand["bbox"] #caixa delimitadora da mão
            center = hand["center"] #centro da mão
            handtype = hand["type"] #direita ou esquerda

            #conta dedos levantados
            fingers = detector.fingersUp(hand)
            totalFinger = fingers.count(1)

            cv2.putText(img, f'{totalFinger} dedo(s)', (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (225, 0, 225), 2)

    #exibe imagem
    cv2.imshow("HAnd Tracking", img)

    if cv2.waitKey(1)&0xFF == ord('q'):
        break
