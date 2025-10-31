from pympler import asizeof
import numpy as np


stars_python = []
for i in range(100_000):
    distance = (i**2 + (i*2)**2)**0.5
    stars_python.append(distance)


positions = np.arange(100_000, dtype=np.float64)
distances = np.sqrt(positions**2 + (positions*2)**2)

python_memory_real = asizeof.asizeof(stars_python)
numpy_memory_real = asizeof.asizeof(distances)

print(f"🐍 Python total memory (deep): {python_memory_real:,} bytes")
print(f"⚡ NumPy total memory (deep): {numpy_memory_real:,} bytes")
print(f"➡️ NumPy uses about {python_memory_real / numpy_memory_real:.1f}× less memory\n")
