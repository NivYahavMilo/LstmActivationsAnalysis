'''
utils for clip classification (cc)
'''
import os

import numpy as np
import torch
from sklearn.metrics import confusion_matrix

import config
from supporting_functions import _dict_to_pkl
from model_training.torch_utils import _to_cpu

K_RUNS = 4  # number of runs for each subject


def _test_time_window(df, window_range: range):
    seq_window = df[df['timepoint'].isin([*window_range])]
    if window_range.start != 0:
        seq_window['timepoint'] = seq_window['timepoint'].apply(
            lambda tr: (tr - window_range.start))
    return seq_window


def _get_clip_labels(timing_file):
    '''
    assign all clips within runs a label
    use 0 for testretest
    '''

    clips = []
    for run in range(K_RUNS):
        run_name = 'MOVIE%d' % (run + 1)  # MOVIEx_7T_yz
        timing_df = timing_file[timing_file['run'].str.contains(run_name)]
        timing_df = timing_df.reset_index(drop=True)

        for jj, row in timing_df.iterrows():
            clips.append(row['clip_name'])

    clip_y = {}
    jj = 1
    for clip in clips:
        if 'testretest' in clip:
            clip_y[clip] = 0
        else:
            clip_y[clip] = jj
            jj += 1

    return clip_y


def _get_mask(X_len, max_length):
    mask = np.zeros((len(X_len), max_length))
    for ii, length in enumerate(X_len):
        mask[ii, :length] = 1

    return mask


def _get_t_acc(y_hat, y, k_time):
    '''
    accuracy as f(time)
    '''
    a = np.zeros(k_time)
    for ii in range(k_time):
        y_i = y[ii::k_time]
        y_hat_i = y_hat[ii::k_time]
        correct = [1 for p, q in zip(y_i, y_hat_i) if p == q]
        a[ii] = sum(correct) / len(y_i)

    return a


def _get_confusion_matrix(y, predicted):
    '''
    if cuda tensor, must move to cpu first
    '''
    y, p = _to_cpu(y), _to_cpu(predicted)

    return confusion_matrix(y, p)


def _lstm_test_acc(model, X, y, X_len, max_length,
                   clip_time, k_sub, args,
                   return_states=False,
                   save_activations=False):
    '''
    masked accuracy for lstm
    per participant accuracy
    '''
    # mask to ignore padding
    mask = _get_mask(X_len, max_length)

    # forward pass
    if return_states:
        _, outputs = model(X, X_len, max_length)
    else:
        outputs = model(X, X_len, max_length)

    if save_activations:
        # save predicted activations
        _dict_to_pkl(model.hidden_activations,
                     os.path.join(config.MODELS_NETWORKS_PATH,
                                  f'{args.net} {args.mode} 10-20 activations'))

    # logits to labels
    _, y_hat = torch.max(outputs, 2)

    # remove padded values
    # converts matrix to vec
    y_hat = y_hat[mask == True]
    y = y[mask == True]

    a = np.zeros(k_sub)
    sub_size = len(y_hat) // k_sub
    for s in range(k_sub):
        # group based on k_sub
        y_hat_s = y_hat[s * sub_size:(s + 1) * sub_size]
        y_s = y[s * sub_size:(s + 1) * sub_size]
        # accuracy for each group
        correct = (y_hat_s == y_s).sum().item()
        a[s] = correct / len(y_s)

    # accuracy as a function of t
    k_class = len(clip_time)
    a_t = {}
    for ii in range(k_class):
        y_i = y[y == ii]
        y_hat_i = y_hat[y == ii]
        k_time = clip_time[ii]
        a_t[ii] = np.zeros((k_sub, k_time))
        sub_size = len(y_hat_i) // k_sub
        for s in range(k_sub):
            # group based on k_sub
            y_hat_s = y_hat_i[s * sub_size:(s + 1) * sub_size]
            y_s = y_i[s * sub_size:(s + 1) * sub_size]
            # accuracy for each group
            a_t[ii][s] = _get_t_acc(y_hat_s, y_s, k_time)

    c_mtx = _get_confusion_matrix(y, y_hat)

    return a, a_t, c_mtx
