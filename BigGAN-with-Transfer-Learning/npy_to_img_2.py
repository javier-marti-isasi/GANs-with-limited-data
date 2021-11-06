import numpy as np
import os
import imageio
from scipy.misc import imsave
image_path = "/media/javier/56102013101FF8A7/MineGAN/MineGANmaster/result2"

def ensure_directory_exist(image_path):
    if not os.path.exists(image_path):
        print("Allocating '{:}'",format(image_path))
        os.mkdir(image_path)


if __name__ == '__main__':
    img_array = np.load('/media/javier/56102013101FF8A7/MineGAN/MineGANmaster/I128_imgs/imgs.npy')
    print(img_array)
    os.makedirs(image_path, exist_ok=True)
    for i, img in enumerate(img_array[:, :]):
        name = "img{}.png".format(i)
        print(i)
        print(img)
        #i_2 = int(i)
        #print(i_2)
        #imsave("./slice_{0}.png".format(i_2), img[i_2, ...])
        #imsave("./slice_{0}.png".format(i), img[i, ...])

        #imageio.imwrite(os.path.join(image_path