import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import colors

import config


def subplot_signal_from_dict(data):
    fig, ax = plt.subplots(len(data), 1, figsize=(7, 5))
    movies = data.keys()
    for a, key in zip(ax, movies):
        x = data[key]

        a.plot(list(x.keys()), list(x.values()))
    plt.title("Last tr clip Correlation with Resting state")
    plt.legend(movies)
    plt.xlabel("Rest TR")
    plt.ylabel("Correlation Value")

    plt.show()

def plot_signals_on_top(data, title):
    correlations = []

    for _seq, _color in zip(data.items(), colors.CSS4_COLORS):
        clip, seq = _seq
        correlations.append({
            "name": clip,
            "x": list(seq.values()),
            "Y": list(seq.keys()),
            'color': colors.CSS4_COLORS[_color],
            'linewidth': 5,


        })

    fig, ax = plt.subplots(figsize=(20,10),)

    for signal in correlations:
        ax.plot(signal['x'],  # signal['y'],
                color=signal['color'],
                linewidth=signal['linewidth'],
                label=signal['name'],
                )

    # Enable legend
    ax.legend(loc="upper right")
    ax.set_title(title)

    plt.xlabel("Rest TR")
    plt.ylabel("Correlation Value")
    plt.show()


def _subplot(table_path, title):
    df = pd.read_csv(table_path, index_col=0)
    plot_signals_on_top(data=df.to_dict(), title=title)


if __name__ == '__main__':
    table_path = f'{config.CORRELATION_MATRIX_BY_TR}\\'\
                 f'fmri last tr clip correlation with rest between without test-re-test.csv'

    _subplot(table_path, "fMRI Last tr clip Correlation with Resting state")

    table_path = f'{config.CORRELATION_MATRIX_BY_TR}\\' \
                 f'last tr clip correlation with rest between without test-re-test.csv'
    title = "LSTM patterns similarity last tr clip with rest between"
    _subplot(table_path, title)