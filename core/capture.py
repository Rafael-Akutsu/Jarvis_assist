import cv2  

cap = cv2.VideoCapture(0)

while True:
    success, img = cap.read()
    img = cv2.flip(img,1)
    
    cv2.imshow("Webcam",img)
    if cv2.waitKey(1)&0xFF == ord('q'):
        break