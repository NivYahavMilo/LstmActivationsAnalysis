import os
import pandas as pd

import config
from mappings.re_arranging import rearrange_clips
from statistical_analysis.correlation_pipelines import (set_activation_vectors,
                                                        auto_correlation_pipeline,
                                                        join_and_auto_correlate,
                                                        total_clip_and_rest_correlation)
from statistical_analysis.math_functions import z_score
from statistical_analysis.matrices_ops import MatricesOperations
from statistical_analysis.table_builder import Mode
from supporting_functions import _load_csv
from visualiztions.plot_figure import plot_matrix


def get_window_tr_clip(mat_clip: pd.DataFrame, length: int = 19, window: str = 'last', tr_range: tuple = ()):
    # getting interest indices
    if window == 'last':
        stop = int(max(mat_clip['tr'].values))
        start = stop - length
    elif window == 'first':
        start = int(min(mat_clip['tr'].values))
        stop = start + length
    elif window == 'custom':
        start = tr_range[0]
        stop = tr_range[1]
    else:
        raise ValueError("Unknown window type")
    start_s: int = mat_clip[mat_clip['tr'] == start].index.values[0]
    stop_s: int = mat_clip[mat_clip['tr'] == stop].index.values[0]
    mat_clip_prune: pd.DataFrame = mat_clip.filter(items=[*range(start_s, stop_s)], axis=0)
    return mat_clip_prune


def auto_correlation_pipeline_custom_tr(subject: str, mode: Mode):
    corr_per_clip = {}
    mat_path = os.path.join(config.ACTIVATION_MATRICES, subject, mode.value, 'activation_matrix.csv')
    sub = _load_csv(mat_path)
    for clip in list(sub['y'].unique()):
        # Drop all columns unrelated to activation values
        mat = sub[sub['y'] == clip]
        mat_pruned = get_window_tr_clip(mat, window='first')
        mat_pruned = mat_pruned.drop(['y', 'tr'], axis=1)
        # normalize matrix values with z-score
        mat_zscore = mat_pruned.apply(lambda x: z_score(x))
        # Calculate Pearson correlation
        pearson_corr = MatricesOperations.correlation_matrix(
            matrix=mat_zscore)
        corr_per_clip[f"{clip}_{mode.value}"] = pearson_corr
    return corr_per_clip


def get_single_tr(mat_clip: pd.DataFrame, clip_name: str, tr_pos: int = -1):
    if tr_pos == -1:
        xdf = mat_clip[mat_clip['y'] == clip_name]
        tr_pos = int(max(xdf['tr'].values))
    activation_series = mat_clip[(mat_clip['tr'] == tr_pos) & (mat_clip['y'] == clip_name)]
    activation_series = activation_series.drop(['y', 'tr'], axis=1)
    return activation_series


def avg_single_tr_vectors(sub_list, mode: Mode, clip):
    clip_per_subs = []
    for sub in sub_list:
        # Execute clip pipeline
        sub_matrix = pd.read_csv(
            os.path.join(config.ACTIVATION_MATRICES, sub, mode.value, 'activation_matrix.csv'))
        activation_vec = get_single_tr(sub_matrix, clip)
        clip_per_subs.append(activation_vec)
    avg_series = MatricesOperations.get_avg_matrix((clip.values for clip in clip_per_subs))
    return avg_series


def compare_cliptorest_single_tr():
    avg_series_per_clip = {}
    for clip in config.idx_to_clip.values():
        clip_vec = avg_single_tr_vectors(config.sub_test_list, Mode.CLIPS, clip)
        rest_vec = avg_single_tr_vectors(config.sub_test_list, Mode.REST_BETWEEN, clip)
        avg_series_per_clip[clip + '_' + Mode.CLIPS.value] = clip_vec.tolist()[0]
        avg_series_per_clip[clip + '_' + Mode.REST_BETWEEN.value] = rest_vec.tolist()[0]
    return pd.DataFrame.from_dict(avg_series_per_clip)


def compare_cliptime_window_to_rest_between(sub_list):
    for sub in sub_list:
        # Execute clip pipeline
        corr_dict = auto_correlation_pipeline_custom_tr(sub, Mode.CLIPS)
        df_clip: pd.DataFrame = set_activation_vectors(corr_dict)
        # Execute rest between pipeline
        corr_: dict = auto_correlation_pipeline(sub, Mode.REST_BETWEEN)
        df_rest: pd.DataFrame = set_activation_vectors(corr_)
        # Merging clips and rest between data frame
        corr_mat = join_and_auto_correlate(df_clip, df_rest)
        corr_mat.to_csv(
            os.path.join(config.ACTIVATION_MATRICES, sub, f'corr_mat_first_19_tr.csv'))
        print('done', sub, 'saved to csv')


def corr_pipe_single_tr(table_name, re_test: bool = False):
    _tr_mat = compare_cliptorest_single_tr()
    _tr_mat = _tr_mat.apply(lambda x: z_score(x))
    _tr_corr = MatricesOperations.correlation_matrix(_tr_mat)
    _tr_corr = rearrange_clips(_tr_corr, where='rows', with_testretest=re_test)
    _tr_corr = rearrange_clips(_tr_corr, where='columns', with_testretest=re_test)
    _tr_corr.to_csv(f'{table_name}.csv')


def main_single_tr_pipe(with_retest=False):
    table = 'last tr corr wb without test re-test'
    corr_pipe_single_tr(table, re_test=with_retest)

    mat = pd.read_csv(f'{table}.csv', index_col=0)
    plot_matrix(mat, table)

    clip_rest_corr = total_clip_and_rest_correlation(table)
    clip_rest_corr.to_csv('rest-clip ' + table + '.csv')


if __name__ == '__main__':
    main_single_tr_pipe(with_retest=False)
