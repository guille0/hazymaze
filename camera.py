from __future__ import print_function
import cv2

from image_parsing import maze_boi

# Capture from camera 0
cap = cv2.VideoCapture(0)
cv2.startWindowThread()

while True:
    _, img = cap.read()

    key = cv2.waitKey(10)
    if key == 27:
        break

    output = maze_boi(img, key)

    cv2.imshow("input", output)

cv2.destroyAllWindows()
cv2.waitKey(1)
cv2.waitKey(1)
cv2.waitKey(1)
cv2.waitKey(1)
cv2.VideoCapture(0).release()
cv2.waitKey(1)
