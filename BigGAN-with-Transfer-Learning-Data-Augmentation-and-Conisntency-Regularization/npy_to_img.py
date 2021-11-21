import matplotlib.pyplot as plt
import numpy as np
import scipy.misc
import os

from skimage.transform import resize
from skimage import data

arr = np.load('/media/javier/56102013101FF8A7/MineGAN/MineGANmaster/I128_imgs/imgs.npy')  # npy file path
print(arr.shape)  # Output the size of the .npy file
# print(arr) # Directly output .npy files


file_dir = "/media/javier/56102013101FF8A7/MineGAN/MineGANmaster/I128_imgs/"  # npyfile path
dest_dir = "/media/javier/56102013101FF8A7/MineGAN/MineGANmaster/result"  # File storage path

def npy_png(file_dir, dest_dir, arr):
    # If the corresponding file does not exist, create a corresponding file
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    file = file_dir + 'imgs.npy'  # npy
    con_arr = np.load(file)  # npy file
    for i in range(0, 200):  # Array The maximum value is the number of pictures (I am 200) The three-dimensional array is: number of pictures horizontal size vertical size
        #arr = con_arr[i, :, :]  # Get a single array of the i-th sheet
        #disp_to_img = scipy.misc.imresize(arr, [375, 1242])  # Modify according to the required size
        #disp_to_img = np.array(Image.fromarray(arr).resize())
        disp_to_img = data.camera()
        resize(disp_to_img, (100, 100))
        plt.imsave(os.path.join(dest_dir, "{}_disp.png".format(i)), disp_to_img, cmap='plasma')  # Define naming rules, save the picture as color mode
        print('photo {} finished'.format(i))


if __name__ == "__main__":
    npy_png(file_dir, dest_dir, arr)