import numpy as np

# Batch-ul de imagini pentru AI
batch = np.random.rand(32, 64, 64, 3)
mean = np.array([0.485, 0.456, 0.406])
std = np.array([0.229, 0.224, 0.225])

# Broadcasting magic - o singură linie!
normalized = (batch - mean) / std
print("Rezultat cu NumPY:", normalized)


print("Fara NumPY: ")
# Fără NumPy ar fi fost:
for i in range(32):           # Pentru fiecare imagine
  for y in range(64):         # Pentru fiecare rând
    for x in range(64):       # Pentru fiecare pixel
      for c in range(3):      # Pentru fiecare canal RGB
        normalized[i,y,x,c] = (batch[i,y,x,c] - mean[c]) / std[c]
# TOTAL: 393,216 operații individuale!


print("Rezultat fara NumPY:", normalized)