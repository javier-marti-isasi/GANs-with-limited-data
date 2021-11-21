#!/bin/bash
# num_save_copies: (Estรก comentado en codigo, no se ejecuta) Save an additional copy to mitigate accidental corruption if process
# num_best_copies: # If improved over previous best metric, save approrpiate copy

#Set-Location -Path "/media/javier/56102013101FF8A7/MineGAN/MineGANmaster"
#--dataset I128_hdf5 --parallel --shuffle  --num_workers 2 --batch_size 100 --resume \
#--num_G_accumulations 8 --num_D_accumulations 8 \
#--num_D_steps 1 --G_lr 1e-4 --D_lr 4e-4 --D_B2 0.999 --G_B2 0.999 \
#--G_ch 96 --D_ch 96 \
#--test_every 2000000 --save_every 100 --num_best_copies 5 --num_save_copies 2 --seed 0 \
# --parallel, para utilizar varias GPUs
# --resume, para hacer fine-tuning (utilizar propio dataset)
# --DiffAugment translation,cutout \
# --num_D_steps 1 --G_lr 1e-4 --D_lr 4e-4 --D_B2 0.999 --G_B2 0.999 \

python train.py \
--dataset I128_hdf5 --shuffle --parallel --num_workers 2 --batch_size 24 --resume \
--DiffAugment translation,cutout,color --mirror_augment \
--num_G_accumulations 8 --num_D_accumulations 8 \
--num_D_steps 1 --G_lr 2e-4 --D_lr 2e-4 --D_B2 0.999 --G_B2 0.999 \
--G_attn 64 --D_attn 64 \
--G_nl inplace_relu --D_nl inplace_relu \
--SN_eps 1e-6 --BN_eps 1e-5 --adam_eps 1e-6 \
--G_ortho 0.0 \
--G_shared \
--G_init ortho --D_init ortho \
--hier --dim_z 120 --shared_dim 128 \
--G_eval_mode \
--which_best FID \
--G_ch 96 --D_ch 96 \
--test_every 79 --save_every 39 --num_best_copies 5 --num_save_copies 2 --seed 0 \
--use_multiepoch_sampler \
--base_root /content/drive/MyDrive/MASTER/TFM/Repositorios/DiffAug/data/your_data \
--experiment_name  experiment_38_diffaug_100_obama_flip_hor_cutout_color \
--num_epochs 150 \
#--data_root  /media/javier/56102013101FF8A7/MineGAN/MineGANmaster/data/your_data/results \
#--ema --use_ema --ema_start 20000 \

#ejemplo otra implementaciรณn:
#--test_every 2000 --save_every 1000 --num_best_copies 5 --num_save_copies 2 --seed 0 \
