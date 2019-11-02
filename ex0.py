#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt

x, y = np.loadtxt('data/xy.txt', unpack=True)

# print(x)
# print(y)

plt.plot(x, y)
plt.show()
