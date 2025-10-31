import numpy as np
import cv2

# Creează o imagine RGB aleatorie 64x64
rgb_image = np.random.randint(0, 256, (1024, 1024, 3), dtype=np.uint8)
print(f"Forma: {rgb_image.shape}")  # (64, 64, 3)

# Extrage canalul roșu
red_channel = rgb_image[:, :, 0]
print(f"Valoare pixel (0,0): R={rgb_image[0,0,0]} G={rgb_image[0,0,1]} B={rgb_image[0,0,2]}")

# --- Afișează imaginea cu OpenCV ---
# Atenție: OpenCV folosește BGR, nu RGB
bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)

cv2.imshow("Random RGB Image", bgr_image)
cv2.waitKey(0)  # Așteaptă o tastă
cv2.destroyAllWindows()
