from os.path import join as pth

import matplotlib.pyplot as plt
import numpy as np
from pandas import date_range, read_csv

from AeroViz.plot.utils import *

# TODO:

# read csv file
blh = read_csv(pth('事件分析.csv'), parse_dates=['Time'], index_col='Time')


@set_figure(figsize=(12, 5))
def event_evolution(_df, **kwargs):
	print(f'Plot : {_df.month[0]}')

	st_tm, fn_tm = _df.index[0], _df.index[-1]
	tick_time = date_range(st_tm, fn_tm, freq='1d')  # set tick

	# seperate day and night
	_df_day = _df.between_time('6:00', '17:00').reindex(date_range(st_tm, fn_tm, freq='1h'))
	_df_night = _df.between_time('18:00', '5:00').reindex(date_range(st_tm, fn_tm, freq='1h'))

	## plot
	fig, ax = plt.subplots()

	## plot background
	shade_value, _ = np.meshgrid(_df['PM2.5'], np.arange((1., 2500), 100))
	ax.pcolormesh(_df.index, np.arange((1., 2500), 100), shade_value, cmap='binary', vmin=0, vmax=300,
				  shading='auto')

	## plot day and night
	ld = ax.scatter(_df.index[0:], _df_day['Ext'], s=50, c='#73b9ff', label='Day Ext', marker='o', alpha=.7)
	ln = ax.scatter(_df.index[0:], _df_night['Ext'], s=50, c='#00238c', label='Night Ext', marker='o', alpha=.7)

	ax2 = ax.twinx()
	# ld, = ax2.plot(_df_day['VC'],c='#FF9797',label='day 06:00~18:00')
	# ln, = ax2.plot(_df_night['VC'],c='#FF0000',label='night 18:00~06:00')
	ld2 = ax2.scatter(_df.index, _df_day['VC'], s=50, c='#FF9797', label='Day VC', marker='o', alpha=.5)
	ln2 = ax2.scatter(_df.index, _df_night['VC'], s=50, c='#FF0000', label='Night VC', marker='o', alpha=.5)

	# add legend on the first axes
	ax.legend(handles=[ld, ln, ld2, ln2], framealpha=0, prop={'weight': 'bold'}, loc='upper left')

	# add xlabel, ylabel, suptitle
	ax.set(xlabel='Date',
		   ylabel='Ext (1/Mm)',
		   xlim=(st_tm, fn_tm),
		   ylim=(1., 600),
		   xticks=tick_time,
		   xticklabels=[_tm.strftime("%F %H:00") for _tm in tick_time])

	ax2.set(ylabel=r'$VC (m^{2}/s)$',
			ylim=(1., 2500))

	fig.suptitle(f'Event evolution ({st_tm.strftime("%F")}_{fn_tm.strftime("%F")})')

	# save figure
	fig.savefig(pth(f"event_evolution_{st_tm.strftime("%F")}_{fn_tm.strftime("%F")}"))


if __name__ == '__main__':
	event_evolution(blh)
