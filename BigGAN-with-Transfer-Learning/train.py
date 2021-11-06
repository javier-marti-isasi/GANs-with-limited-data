""" BigGAN: The Authorized Unofficial PyTorch release
    Code by A. Brock and A. Andonian
    This code is an unofficial reimplementation of
    "Large-Scale GAN Training for High Fidelity Natural Image Synthesis,"
    by A. Brock, J. Donahue, and K. Simonyan (arXiv 1809.11096).

    Let's go.
"""
print("="*150)
print("ESTAMOS EN train.py")
print("="*150)

#Javier avoid “CUDA out of memory” in PyTorch
#import torch
#torch.cuda.empty_cache()

#Javier
#import os
#os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
#os.environ["CUDA_VISIBLE_DEVICES"]="0"  # specify which GPU(s) to be used

import os
import functools
import math
import numpy as np
from tqdm import tqdm, trange


import torch
import torch.nn as nn
from torch.nn import init
import torch.optim as optim
import torch.nn.functional as F
from torch.nn import Parameter as P

# Import my stuff
import inception_utils
import utils
import losses
import train_fns
from sync_batchnorm import patch_replication_callback
import pdb

# The main training file. Config is a dictionary specifying the configuration
# of this training run.
def run(config):

  # Update the config dict as necessary
  # This is for convenience, to add settings derived from the user-specified
  # configuration into the config-dict (e.g. inferring the number of classes
  # and size of the images from the dataset, passing in a pytorch object
  # for the activation specified as a string)
  config['resolution'] = utils.imsize_dict[config['dataset']]
  config['n_classes'] = utils.nclass_dict[config['dataset']]
  config['G_activation'] = utils.activation_dict[config['G_nl']]
  config['D_activation'] = utils.activation_dict[config['D_nl']]
  # By default, skip init if resuming training.
  if config['resume']:
    print('Skipping initialization for training resumption...')
    config['skip_init'] = True
  config = utils.update_config_roots(config)
  device = 'cuda'
  
  # Seed RNG
  utils.seed_rng(config['seed'])

  # Prepare root folders if necessary
  utils.prepare_root(config)

  # Setup cudnn.benchmark for free speed
  torch.backends.cudnn.benchmark = True

  # Import the model--this line allows us to dynamically select different files.
  model = __import__(config['model'])
  experiment_name = (config['experiment_name'] if config['experiment_name']
                       else utils.name_from_config(config))
  print('Experiment name is %s' % experiment_name)
  # Next, build the model
  # Minor
  M = model.Minor(**config).to(device)
  G = model.Generator(**config).to(device)
  D = model.Discriminator(**config).to(device)
  
   # If using EMA, prepare it
  if config['ema']:
    print('Preparing EMA for G with decay of {}'.format(config['ema_decay']))
    G_ema = model.Generator(**{**config, 'skip_init':True, 
                               'no_optim': True}).to(device)
    ema = utils.ema(G, G_ema, config['ema_decay'], config['ema_start'])
  else:
    G_ema, ema = None, None
  
  # FP16?
  if config['G_fp16']:# yaxing: hert it is False 
    print('Casting G to float16...')
    G = G.half()
    if config['ema']:
      G_ema = G_ema.half()
  if config['D_fp16']:# yaxing: hert it is False
    print('Casting D to fp16...')
    D = D.half()
    # Consider automatically reducing SN_eps?
  GD = model.G_D(G, D, M)
  print(G)
  print(D)
  print(M)
  print('Number of params in G: {} D: {} M: {}'.format(
    *[sum([p.data.nelement() for p in net.parameters()]) for net in [G,D,M]]))
  # Prepare state dict, which holds things like epoch # and itr #
  state_dict = {'itr': 0, 'epoch': 0, 'save_num': 0, 'save_best_num': 0,
                'best_IS': 0, 'best_FID': 999999, 'config': config}

  # If loading from a pre-trained model, load weights
  if config['resume']:
    print('Loading weights...')
    utils.load_weights(G, D, M, state_dict,
                       config['weights_root'], experiment_name, 
                       config['load_weights'] if config['load_weights'] else None,
                       G_ema if config['ema'] else None,
                       load_optim=(not config['reset_optim']),
                       strict=(not config['reset_optim']))

  # If parallel, parallelize the GD module
  if config['parallel']:
    GD = nn.DataParallel(GD)
    if config['cross_replica']:
      patch_replication_callback(GD)

  # Prepare loggers for stats; metrics holds test metrics,
  # lmetrics holds any desired training metrics.
  test_metrics_fname = '%s/%s_log.jsonl' % (config['logs_root'],
                                            experiment_name)
  train_metrics_fname = '%s/%s' % (config['logs_root'], experiment_name)
  print('Inception Metrics will be saved to {}'.format(test_metrics_fname))
  test_log = utils.MetricsLogger(test_metrics_fname, 
                                 reinitialize=(not config['resume']))
  print('Training Metrics will be saved to {}'.format(train_metrics_fname))
  train_log = utils.MyLogger(train_metrics_fname, 
                             reinitialize=(not config['resume']),
                             logstyle=config['logstyle'])
  # Write metadata
  utils.write_metadata(config['logs_root'], experiment_name, config, state_dict)
  # Prepare data; the Discriminator's batch size is all that needs to be passed
  # to the dataloader, as G doesn't require dataloading.
  # Note that at every loader iteration we pass in enough data to complete
  # a full D iteration (regardless of number of D steps and accumulations)
  D_batch_size = (config['batch_size'] * config['num_D_steps']
                  * config['num_D_accumulations'])
  loaders = utils.get_data_loaders(**{**config, 'batch_size': D_batch_size,
                                      'start_itr': state_dict['itr']})

  # Prepare inception metrics: FID and IS
  get_inception_metrics = inception_utils.prepare_inception_metrics(config['dataset'], config['parallel'], config['no_fid'])

  # Prepare noise and randomly sampled label arrays
  # Allow for different batch sizes in G
  G_batch_size = max(config['G_batch_size'], config['batch_size'])
  z_, y_ = utils.prepare_z_y(G_batch_size, G.dim_z, config['n_classes'],
                             device=device, fp16=config['G_fp16'])
  # Prepare a fixed z & y to see individual sample evolution throghout training
  fixed_z, fixed_y = utils.prepare_z_y(G_batch_size, G.dim_z,
                                       config['n_classes'], device=device,
                                       fp16=config['G_fp16'])  
  fixed_z.sample_()
  fixed_y.sample_()
  # Loaders are loaded, prepare the training function
  if config['which_train_fn'] == 'GAN': # yaxing: here it is  GAN 
    train = train_fns.GAN_training_function(G, D, M, GD, z_, y_, 
                                            ema, state_dict, config)
  # Else, assume debugging and use the dummy train fn
  else:
    train = train_fns.dummy_training_function()
  # Prepare Sample function for use with inception metrics
  sample = functools.partial(utils.sample,
                              G=(G_ema if config['ema'] and config['use_ema']
                                 else G), M=M,
                              z_=z_, y_=y_, config=config)
  # Javier
  state_dict['epoch'] = 0
  print('Beginning training at epoch %d...' % state_dict['epoch'])
  # Train for specified number of epochs, although we mostly track G iterations.
  print("num_epochs")
  print(config['num_epochs'])
  #Javier
  for epoch in range(state_dict['epoch'], config['num_epochs']):
  #for epoch in range(state_dict['epoch'], 11):
    # Which progressbar to use? TQDM or my own?
    print("="*150)
    print("state_dict['epoch']: " + str(state_dict['epoch']))
    print("=" * 150)
    if config['pbar'] == 'mine':# yaxing: hert it is 'mine' 
      pbar = utils.progress(loaders[0],displaytype='s1k' if config['use_multiepoch_sampler'] else 'eta')
    else:
      pbar = tqdm(loaders[0])
    acc_metrics = {}
    acc_itrs = 0
    for i, (x, y) in enumerate(pbar):
      # Make sure G and D are in training mode, just in case they got set to eval
      # For D, which typically doesn't have BN, this shouldn't matter much.
      #print("G.train()")
      G.train()
      #print("D.train()")
      D.train()
      #print("H.train()")
      M.train()
      if config['ema']:
        G_ema.train()
      if config['D_fp16']: # yaxing: hert it is False
        x, y = x.to(device).half(), y.to(device)
      else:
        x, y = x.to(device), y.to(device)
      if state_dict['itr'] < (138000 + 300): # 138000 is the last iteration of the BigGAN  
          stage = 1
      else:
          stage = 2

      metrics = train(x, y, stage)
      train_log.log(itr=int(state_dict['itr']), **metrics)

      for k, v in metrics.items():
        if k not in acc_metrics:
          acc_metrics[k] = 0
        acc_metrics[k] += v
      acc_itrs += 1
      
      # Every sv_log_interval, log singular values
      if (config['sv_log_interval'] > 0) and (not (state_dict['itr'] % config['sv_log_interval'])):
        train_log.log(itr=int(state_dict['itr']), 
                      **{**utils.get_SVs(G, 'G'), **utils.get_SVs(D, 'D')})

      # If using my progbar, print metrics.
      if config['pbar'] == 'mine':
          print(', '.join(['itr: %d' % state_dict['itr']] 
                           + ['%s : %+4.3f' % (key, metrics[key])
                           for key in metrics]), end=' ')

      # Save weights and copies as configured at specified interval
      if not (state_dict['itr'] % config['save_every']):
        if config['G_eval_mode']:
          print('Switchin G to eval mode...')
          #print("G.eval()")
          G.eval()
          #print("G.eval()")
          M.eval()
          if config['ema']:
            G_ema.eval()
        train_fns.save_and_sample(G, D, M, G_ema, z_, y_, fixed_z, fixed_y,
                                  state_dict, config, experiment_name)

      # Test every specified interval

      '''
      if not (state_dict['itr'] % config['test_every']):
        if config['G_eval_mode']:
          print('Switchin G to eval mode...')
          #print("G.eval()_2")
          G.eval()
          #print("H.eval()_2")
          M.eval()
        train_fns.test(G, D, G_ema, z_, y_, state_dict, config, sample,
                       get_inception_metrics, experiment_name, test_log)
      '''

      # DiffAug
      if not (state_dict['itr'] % config['test_every']):
        if config['G_eval_mode']:
          print('Switchin G to eval mode...')
          G.eval()
        train_fns.test(G, D, GD, G_ema, z_, y_, state_dict, config, sample,
                       get_inception_metrics, experiment_name, test_log, acc_metrics, acc_itrs)
        for k in acc_metrics.keys():
          acc_metrics[k] = 0
        acc_itrs = 0
      # Increment the iteration counter
      state_dict['itr'] += 1

    # Increment epoch counter at end of epoch
    state_dict['epoch'] += 1

  # DiffAug
  # Final evaluation
  if config['G_eval_mode']:
    print('Switchin G to eval mode...')
    G.eval()
    if config['ema']:
      G_ema.eval()
  train_fns.save_and_sample(G, D, M, G_ema, z_, y_, fixed_z, fixed_y,
                            state_dict, config, experiment_name)
  train_fns.test(G, D, GD, G_ema, z_, y_, state_dict, config, sample,
                 get_inception_metrics, experiment_name, test_log, acc_metrics, acc_itrs)


def main():
  # parse command line and run
  parser = utils.prepare_parser()
  config = vars(parser.parse_args())
  print(config)
  run(config)

if __name__ == '__main__':
  main()
