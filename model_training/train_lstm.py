import numpy as np
import pandas as pd
import pickle
import os
import time

import config
from enums import Mode
from model_training.hyperparameters import HyperParams
from supporting_functions import _dict_to_pkl
import torch
import torch.nn as nn
from model_training.models import LSTMClassifier

from model_training.cc_utils import _lstm_test_acc, _test_time_window
from dataloader import _get_clip_seq as _get_seq
from dataloader import _clip_class_df

K_SEED = 330


def _test(df, args):
    '''
    test subject results
    view only for best cross-val parameters
    '''
    # set pytorch device
    torch.manual_seed(K_SEED)
    use_cuda = torch.cuda.is_available()
    args.device = torch.device('cuda:0' if use_cuda else 'cpu')
    if use_cuda:
        print('cuda')
    else:
        print('cpu')

    # get X-y from df
    subject_list = df['Subject'].unique()
    train_list = subject_list[:args.train_size]
    test_list = subject_list[args.train_size:]

    features = [ii for ii in df.columns if 'feat' in ii]
    k_feat = len(features)
    print('number of classes = %d' % (args.k_class))

    df = _test_time_window(df, window_range=range(0, 10))

    # length of each clip
    clip_time = np.zeros(args.k_class)
    for ii in range(args.k_class):
        class_df = df[df['y'] == ii]
        clip_time[ii] = np.max(np.unique(class_df['timepoint'])) + 1
    clip_time = clip_time.astype(int)  # df saves float
    print('seq lengths = %s' % clip_time)

    # results dict init
    results = {}

    # mean accuracy across time
    results['train'] = np.zeros(len(test_list))
    results['val'] = np.zeros(len(test_list))

    # per class temporal accuracy
    results['t_train'] = {}
    results['t_test'] = {}
    for ii in range(args.k_class):
        results['t_train'][ii] = np.zeros(
            (len(test_list), clip_time[ii]))
        results['t_test'][ii] = np.zeros(
            (len(test_list), clip_time[ii]))
    '''
    init model
    '''
    model = LSTMClassifier(k_feat, args.k_hidden,
                           args.k_layers, args.k_class)
    model.fc.register_forward_hook(model.hook)
    model.to(args.device)
    print(model)

    lossfn = nn.CrossEntropyLoss(ignore_index=-100)
    # if input is cuda, loss function is auto cuda
    opt = torch.optim.Adam(model.parameters())

    # get train, test sequences
    X_train, train_len, y_train = _get_seq(df,
                                           train_list, args)
    X_test, test_len, y_test = _get_seq(df,
                                        test_list, args)

    max_length = torch.max(train_len)
    '''
    train classifier
    '''
    permutation = torch.randperm(X_train.size()[0])
    losses = np.zeros(args.num_epochs)
    #
    then = time.time()

    for epoch in range(args.num_epochs):
        for i in range(0, X_train.size()[0], args.batch_size):
            indices = permutation[i:i + args.batch_size]
            batch_x, batch_y = X_train[indices], y_train[indices]
            batch_x_len = train_len[indices]

            y_pred = model(batch_x, batch_x_len, max_length)
            loss = lossfn(y_pred.view(-1, args.k_class),
                          batch_y.view(-1))

            opt.zero_grad()
            loss.backward()
            opt.step()

        losses[epoch] = loss

    print(losses)
    print('--- train time =  %0.4f seconds ---' % (time.time() - then))
    # torch.save(model, f"{args.net} {args.mode.value} 10-20 tr.pt")
    '''
    results on test data
    '''
    a, a_t, c_mtx = _lstm_test_acc(model, X_test, y_test,
                                   test_len, max_length, clip_time,
                                   len(test_list), args,
                                   save_activations=False)
    results['test'] = a
    print('sacc = %0.3f' % np.mean(a))
    for ii in range(args.k_class):
        results['t_test'][ii] = a_t[ii]
    results['test_conf_mtx'] = c_mtx

    return results


def run_net(args):
    nets_path = os.path.join(config.FMRI_DATA_NETWORKS, args.mode)
    networks = os.listdir(nets_path)
    for net in networks:
        args.net = net.replace('df', '').replace('.pkl', '')
        res_path = f'results {args.net} {args.mode}.pkl'
        print(f"start training {args.net} in {args.mode} mode")
        df = pd.read_pickle(os.path.join(config.FMRI_DATA_NETWORKS,
                                         args.mode, net))
        results = {'test_mode': _test(df, args)}
        with open(res_path, 'wb') as f:
            pickle.dump(results, f)

def run(args):
    df = pd.read_pickle(os.path.join(config.FMRI_DATA,
                                     f"4_runs_{args.mode.value}.pkl"))
    res_path = os.path.join(config.RESULTS_PATH, f'300 roi {args.mode.value} 0-10 tr results')
    results = {'test_mode': _test(df, args)}
    with open(f'{res_path}.pkl', 'wb') as f:
        pickle.dump(results, f)

def create_pkl_df(args):
    df = _clip_class_df(args)
    df.to_pickle(f"4_runs_{args.mode.value}.pkl")



if __name__ == '__main__':
    hp = HyperParams()
    hp.mode = Mode.REST_BETWEEN
    run(args=hp)
