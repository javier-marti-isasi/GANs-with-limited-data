#!/bin/bash

#ATENCION!!!!! SI SE HACE UN NUEVO DATASET, HAY QUE MOVER/ELIMINAR LOS ARCHIVOS DE MineGAN/MineGANmaster:
 # I128_hdf5_inception_activations.npz
 # I128_imgs.npz
 # I128_inception_moments.npz

#python make_hdf5.py --dataset I128 --batch_size 256 --data_root /media/yaxing/Elements/IIAI_raid/Imagenet/single_cate
#python calculate_inception_moments.py --dataset I128_hdf5 --data_root /media/yaxing/Elements/IIAI_raid/Imagenet/single_cate
#python make_hdf5.py --dataset I128 --batch_size 256 --data_root /media/javier/56102013101FF8A7/MineGAN/MineGANmaster/styleGANv2/data/CatHead
#python make_hdf5.py --dataset I128 --batch_size 256 --data_root /media/javier/56102013101FF8A7/MineGAN/MineGANmaster/styleGANv2/data/PandaHead
#python calculate_inception_moments.py --dataset I128_hdf5 --data_root /media/javier/56102013101FF8A7/MineGAN/MineGANmaster/styleGANv2/data/PandaHead

python make_hdf5.py --dataset I128 --batch_size 256 --data_root /media/javier/56102013101FF8A7/MineGAN/MineGANmaster/datasets/1000_dogs
python calculate_inception_moments.py --dataset I128_hdf5 --data_root /media/javier/56102013101FF8A7/MineGAN/MineGANmaster/datasets/1000_dogs