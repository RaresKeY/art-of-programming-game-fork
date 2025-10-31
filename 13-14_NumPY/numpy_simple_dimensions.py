import numpy as np


heartbeat = np.array([72, 75, 78, 74, 71, 73, 76, 79])
print(f"Forma: {heartbeat.shape}")  # (8,)
print(f"Puls mediu: {np.mean(heartbeat)} BPM")


room_temp = np.array([
    [22.5, 23.1],
    [22.7, 24.2],
    [22.4, 23.8]
])
print(f"Forma: {room_temp.shape}")  # (3, 2)
print(f"Temperatura medie: {np.mean(room_temp)}°C")


print()


rgb_image = np.random.randint(0, 256, (64, 64, 3))
print(f"Forma: {rgb_image.shape}")  # (64, 64, 3)
red_channel = rgb_image[:, :, 0]  # Extrage canalul roșu
print(f"Valoare pixel (0,0): R={rgb_image[0,0,0]} G={rgb_image[0,0,1]} B={rgb_image[0,0,2]}")



print()

batch_images = np.random.rand(32, 64, 64, 3)
print(f"Forma batch: {batch_images.shape}")  # (32, 64, 64, 3)
print(f"Prima imagine: {batch_images[0].shape}")  # (64, 64, 3)
print(f"Total parametri: {batch_images.size:,} float-uri")  # 393,216!