"""
Dose volume histogram plotting utilities.

Provides :class:`DVHPlot` and :class:`CasePlotter` for conveniently
plotting DVH curve data generated by calling :func:`Case.plan`.

Attributes:
	PLOTTING_INSTALLED (:obj:`bool`): ``True`` if :mod:`matplotlib` is
		not available. If so, :class:`DVHPlot` and :class:`CasePlotter`
		types are replaced with lambdas that match the initialization
		argument signature and each yield ``None`` instead.

		If :mod:`matplotlib` *is* available, the :class:`DVHPlot` and
		:class:`CasePlotter` types are defined normally.

		This switch allows :mod:`conrad` to install, load and operate
		without Python plotting capabilities, and exempts
		:mod:`matplotlib` from being a load-time requirement.
"""
"""
Copyright 2016 Baris Ungun, Anqi Fu

This file is part of CONRAD.

CONRAD is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CONRAD is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CONRAD.  If not, see <http://www.gnu.org/licenses/>.
"""
from conrad.compat import *

from os import path
from math import ceil
from numpy import linspace
from os import getenv

from conrad.defs import module_installed
from conrad.optimization.history import RunRecord
from conrad.case import Case

# allow for CONRAD use without plotting by making visualization types
# optional
if module_installed('matplotlib'):
	PLOTTING_INSTALLED = True

	import matplotlib
	if getenv('DISPLAY') is not None:
		import matplotlib.pyplot as plt
		SHOW = plt.show
	else:
		matplotlib.use('Agg')
		import matplotlib.pyplot as plt
		SHOW = lambda : None

	from matplotlib.pyplot import get_cmap
	from matplotlib.colors import LinearSegmentedColormap
else:
	PLOTTING_INSTALLED = False


def panels_to_cols(n_panels):
	"""
	Convert number of panels to number of subplot columns.

	Used to standardize and balance subplot layout when using multiple
	plans. Prioritizes horizontal expansion over vertical expansion up
	to a maximum of 4 columns.

	Args:
		n_panels (:obj:`int`): number of subplot panels.

	Returns:
		:obj:`int`: number of subplot columns.

	Raises:
		None
	"""
	n_cols = 1
	if n_panels > 1:
		n_cols += 1
	if n_panels > 4:
		n_cols += 1
	if n_panels > 6:
		n_cols += 1
	return n_cols

if not PLOTTING_INSTALLED:
	DVHPlot = lambda arg1, arg2: None
	CasePlotter = lambda arg1: None
else:
	class DVHPlot(object):
		"""
		Tool for visualizing dose volume histograms.

		Figure contains :attr:`~DVHPlot.n_structures` dose volume
		histograms distributed among (:attr:`~DVHPlot.cols` by
		:attr:`~DVHPlot.rows`) subplots. This can be adjusted
		dynamically by changing the subplot indices assigned to each
		series.

		Attributes:
			fig (:class:`matplotlib.Figure`): Canvas for rendering
				dose volume histograms.
			n_structures (:obj:`int`): Number of structures for which to
				render DVH curves.
		"""

		def __init__(self, panels_by_structure, names_by_structure):
			"""
			Initialize :class:`DVHPlot`.

			Initialize a :class:`matplotlib.Figure` as a blank canvas.
			Private dictionaries track panel (subplot index), series
			names, and series color assignments, all keyed by structure
			labels. Arguments set series names and subplot indices.

			Args:
				 panels_by_structure (:obj:`dict`): Dictionary of series
				 	subplot indices keyed by series (structure) labels.
				 names_by_structure: (:obj:`dict`): Dictionary of series
				 	names keyed by series (structure) labels.
			"""
			self.fig = plt.figure()
			self.__panels_by_structure = {}
			self.__names_by_structure = {}
			self.__colors_by_structure = {}
			self.__cols = 1
			self.__rows = 1

			self.n_structures = len(panels_by_structure)
			self.series_names = names_by_structure
			self.series_panels = panels_by_structure

			# set colors using default scheme to start
			self.autoset_series_colors()

		@property
		def series_panels(self):
			"""
			Dictionary of series subplot indices keyed by series labels.
			"""
			return self.__panels_by_structure

		@property
		def rows(self):
			""" Number of subplot rows. """
			return self.__rows

		@property
		def cols(self):
			""" Number of subplot columns. """
			return self.__cols

		@property
		def n_panels(self):
			""" Total number of suplots. """
			return self.cols * self.rows

		@series_panels.setter
		def series_panels(self, panels_by_structure):
			self.__panels_by_structure = {}
			n_panels = 1
			for label in panels_by_structure:
				panel = panels_by_structure[label]
				self.__panels_by_structure[label] = panel
				n_panels = max(n_panels, panel)

			# subplot dimensions
			self.__cols = panels_to_cols(n_panels)
			self.__rows = int(ceil(float(n_panels) / self.__cols))

		@property
		def series_names(self):
			""" Dictionary of series names keyed by series labels. """
			return self.__names_by_structure

		@series_names.setter
		def series_names(self, names_by_structure):
			self.__names_by_structure = {}
			for label in names_by_structure:
				self.__names_by_structure[label] = names_by_structure[label]

		@property
		def series_colors(self):
			""" Dictionary of series colors keyed by series labels. """
			return self.__colors_by_structure

		@series_colors.setter
		def series_colors(self, colors_by_structure):
			for label in colors_by_structure:
				self.__colors_by_structure[label] = colors_by_structure[label]

		def autoset_series_colors(self, structure_order_dict=None,
								  colormap=None):
			"""
			Set series colors with (possibly default) :class:`LinearSegmentedColormap`.

			Args:
				structure_order_dict (:obj:`dict`, optional): Dictionary
					mapping series (i.e., structure) label keys to int
					values that give the rank-order of the series;
					permuting order allows different colors to be
					assigned to different series.
				colormap (:obj:`str`, optional) Assumed to be valid
					:mod:`matplotlib.pyplot` colormap name.

			Returns:
				None
			"""
			if isinstance(colormap, LinearSegmentedColormap):
				colors = listmap(colormap, linspace(
						0.1, 0.9, self.n_structures))
			else:
				cmap = get_cmap('rainbow')
				colors = listmap(cmap, linspace(
						0.9, 0.1, self.n_structures))

			for idx, label in enumerate(self.series_panels.keys()):
				if structure_order_dict is not None:
					self.series_colors[label] = colors[structure_order_dict[label]]
				else:
					self.series_colors[label] = colors[idx]


		def plot(self, plot_data, show=False, clear=True, xmax=None, legend=True,
				 title=None, self_title=False, large_markers=False,
				 suppress_constraints=False, suppress_xticks=False,
				 suppress_yticks=False, x_label='Dose (Gy)',
				 suppress_xlabel=False, y_label='Percentile',
				 suppress_ylabel=False, legend_coordinates=None,
				 legend_alignment=None, **options):
			"""
			Plot ``plot_data`` to the object's :class:`matplotlib.Figure`.

			The input ``plot_data`` should a :obj:`dict` with the
			following scheme::

				{
					series_label_1: {
						curve: {
							dose: numpy.ndarray, # (x data)
							percentile: numpy.ndarray # (y data)
						},
						constraints:[
							{
								dose: [float, float], #(value, value +/- slack)
							  	percentile: [float, float],
							  	symbol: char #(i.e., '<' or '>')
							 }, ...
						]
					},
					...
				}

			Args:
				plot_data (:obj:`dict`) Collection of DVH curves, keyed
					by structure/series label, with format specified
					above.
				show (:obj:`bool`, optional): Show
					:class:`matplotlib.Figure` canvas after
					``plot_data`` elements are drawn.
				clear (:obj:`bool`, optional): Clear
					:class:`matplotlib.Figure` before ``plot_data``
					elements are drawn.
				xmax (:obj:`float`, optional): Upper limit for x-axis
					set to this value if provided. Otherwise, upper
					limit set to 110% of largest dose encountered in
					``plot_data``.
				legend (:obj:`bool`, optional): Enable legend in
					:class:`matplotlib.Figure`.
				title (:obj:`str`, optional): Contents drawn as title of
					:class:`matplotlib.Figure`.
				large_markers (:obj:`bool`, optional): Draw dose volume
					constraints with larger size markers.
				suppress_constraints (:obj:`bool`, optional): Suppress
					rendering of dose volume constraints.
				suppress_xticks (:obj:`bool`, optional): Suppress
					drawing of x-axis ticks.
				suppress_yticks (:obj:`bool`, optional): Suppress
					drawing of y-axis ticks.
				x_label (:obj:`str`, optional): x-axis label.
				suppress_xlabel (:obj:`bool`, optional): Suppress
					drawing of x-axis label.
				y_label (:obj:`str`, optional): y-axis label.
				suppress_ylabel (:obj:`bool`, optional): Suppress
					drawing of y-axis label.
				legend_coordinates (:obj:`list`, optional): Position, as
				 	(x,y)-coordinates, of legend anchor relative to
				 	figure; passed as kewyword argument ``bbox_to_anchor``
				 	in  :meth:`matplotlib.Figure.legend`.
				legend_alignment (:obj:`str`, optional): String defining
					alignment of legend relative to anchor, passed as
					keyword argument ``loc`` in
					:meth:`matplotlib.Figure.legend`.
				**options: Arbitrary keyword arguments, passed to
					:meth:`matplotlib.Figure.plot`.

			Returns:
				None
			"""
			if clear:
				self.fig.clf()

			max_dose = max([
					data['curve']['dose'].max() for
					data in plot_data.values()])
			marker_size = 16 if large_markers else 12

			for label, data in plot_data.items():
				plt.subplot(
						self.__rows, self.__cols,
						self.series_panels[label])

				color = self.series_colors[label]
				name = self.series_names[label] if legend else '_nolegend_'

				plt.plot(data['curve']['dose'], data['curve']['percentile'],
					color=color, mfc=color, mec=color, label=name, **options)
				if self_title:
					plt.title(name)
				elif title is not None:
					plt.title(title)

				if data['rx'] > 0:
					plt.axvline(x=data['rx'], linewidth=1, color=color,
								linestyle='dotted', label='_nolegend_')

				if suppress_constraints:
					continue

				for constraint in data['constraints']:
					# TODO: What should we plot for other constraints like mean, min, max, etc?
					if constraint[1]['type'] is 'percentile':
						plt.plot(
								constraint[1]['dose'][0],
								constraint[1]['percentile'][0],
								constraint[1]['symbol'], alpha=0.55,
								color=color, markersize=marker_size,
								label='_nolegend_', **options)
						plt.plot(
								constraint[1]['dose'][1],
								constraint[1]['percentile'][1],
								constraint[1]['symbol'], label='_nolegend_',
								color=color, markersize=marker_size, **options)
						slack = abs(constraint[1]['dose'][1] -
									constraint[1]['dose'][0])
						if slack > 0.1:
							plt.plot(constraint[1]['dose'],
									 constraint[1]['percentile'], ls='-',
									 alpha=0.6, label='_nolegend_',
									 color=color)

						# So we don't cut off DVH constraint labels
						max_dose = max(max_dose, constraint[1]['dose'][0])

			xlim_upper = xmax if xmax is not None else 1.1 * max_dose

			plt.xlim(0, xlim_upper)
			plt.ylim(0, 103)
			if suppress_yticks:
				plt.yticks([])
			else:
				plt.yticks(fontsize=14)
			if suppress_xticks:
				plt.suppress_xticks([])
			else:
				plt.yticks(fontsize=14)
			if not suppress_xlabel:
				plt.xlabel(str(x_label), fontsize=16)
			if not suppress_ylabel:
				plt.ylabel(str(y_label), fontsize=16)
			if legend:
				legend_args = {
					'ncol':1,
					'loc':'upper right',
					'columnspacing':1.0,
					'labelspacing':0.0,
					'handletextpad':0.0,
					'handlelength':1.5,
					'fancybox':True,
					'shadow':True
				}
				if legend_alignment is not None:
					legend_args['loc'] = legend_alignment
				if legend_coordinates is not None:
					legend_args['bbox_to_anchor'] = legend_coordinates
				plt.legend(**legend_args)

			if show:
				SHOW()

		def save(self, filepath, overwrite=True, verbose=False):
			"""
			Save the object's current plot to ``filepath``.

			Args:
				filepath (:obj:`str`): Specify path to save plot.
				overwrite (bool):, Allow overwrite of file at
					``filepath``if ``True``.
				verbose (:obj:`bool`): Print confirmation of save if
					``True``.

			Returns:
				None

			Raises:
				ValueError: If ``filepath`` does not exist *or* is an
					existing file and flag ``overwrite`` is ``False``.
				RuntimeError: If save fails for any other reason.
			"""
			filepath = path.abspath(filepath)
			directory = path.dirname(filepath)
			if not path.isdir(path.dirname(filepath)):
				raise ValueError(
						'argument "filepath" specified with invalid'
						'directory')
			elif not overwrite and path.exists(filepath):
				raise ValueError(
						'argument "filepath" specifies an existing file'
						'and argument "overwrite" is set to False')
			else:
				try:
					if verbose:
						print("SAVING TO ", filepath)
					plt.savefig(filepath, bbox_inches='tight')
				except:
					raise RuntimeError(
							'could not save plot to file: {}'.format(filepath))

		def __del__(self):
			"""
			Close object's :class:`matplotlib.Figure` when out of scope.
			"""
			plt.close(self.fig)

	class CasePlotter(object):
		"""
		Wrap :class:`DVHPlot` for visualizing treatment plan data.

		Attributes:
			dvh_plot (:class:`DVHPlot`): Dose volume histogram plot.

		Examples:
			>>> # intialize based on an existing :class:`Case` object "case"
			>>> plotter = CasePlotter(case)

			>>> # form treatment plan with case
			>>> _, run = case.plan(**args)

			>>> # plot the output emitted by the case.plan() call
			>>> plotter.plot(run, **options)
		"""

		def __init__(self, case):
			"""
			Initialize :class:`CasePlotter`.

			Use structure information from ``case`` to initialize a
			:class:`DVHPlot` object with the names and labels of each
			structure associated with the case.

			Args:
				case (:class:`Case`): Treatment planning case to use as
					basis for configuring object's :class:`DVHPlot`

			Raises:
				TypeError: If argument is not of type :class:`Case`
			"""
			if not isinstance(case, Case):
				TypeError('argument "case" must be of type conrad.Case')

			# plot setup
			panels_by_structure = {label: 1 for label in case.anatomy.label_order}
			names_by_structure = {
					label: case.anatomy[label].name for
					label in case.anatomy.label_order}
			self.dvh_plot = DVHPlot(panels_by_structure, names_by_structure)
			self.__labels = {}
			for s in case.anatomy:
				self.__labels[s.label] = s.label
				self.__labels[s.name] = s.label

		def label_is_valid(self, label):
			return label in self.__labels

		def set_display_groups(self, grouping='together', group_list=None):
			"""
			Specify structure-to-panel assignments for display.

			Args:
				grouping (:obj:`str`, optional): Should be one of
					'together', 'separate', or 'list'. If 'together',
					all curves plotted on single panel. If 'separate',
					each curve plotton on its own panel. If 'list',
					curves grouped according to ``group_list``.
				group_list (:obj:`list` of :obj:`tuple`, optional): If
						provided, each element of the i-th :obj:`tuple`
						is assumed to be a valid structure label, and
						the DVH curve for the corresponding structure is
						assigned to panel i.

			Returns:
				None

			Raises:
				TypeError: If ``grouping`` is not a :obj:`str` or
					members of ``group_list`` are not each a
					:obj:`tuple`.
				ValueError: If ``grouping`` is not one of ('together',
					separate', 'list'); *or* if each label in each tuple
					in ``group_list`` does not correspond to a structure
					label in the case used to initialize this
					:class:`CasePlotter`.
			"""

			if not isinstance(grouping, str):
				raise TypeError('argument "grouping" must be of type {}'
								''.format(str))
			if grouping not in ('together', 'separate', 'list'):
				raise ValueError('argument "grouping" must be one of '
								 'the following: ("together", '
								 '"separate", or "list")')

			if grouping == 'together':
				for k in self.dvh_plot.series_panels:
					self.dvh_plot.series_panels[k] = 1
			elif grouping == 'separate':
				for i, k in enumerate(self.dvh_plot.series_panels):
					self.dvh_plot.series_panels[k] = i + 1
			elif grouping == 'list':
				valid = isinstance(group_list, list)
				valid &= all(map(lambda x: isinstance(x, tuple), group_list))
				if valid:
					for i, group in enumerate(group_list):
						for label in group:
							if label in self.__labels:
								self.dvh_plot.series_panels[
										self.__labels[label]] = i + 1
							else:
								raise ValueError(
										'specified label {} in tuple {} '
										'does not correspond to any '
										'known structure labels in the '
										'current case'
										''.format(label, group))
				else:
					raise TypeError('argument "group_list" must be a {} '
									'of {}s'.format(list, tuple))


		def plot(self, data, second_pass=False, show=False, clear=True,
				 subset=None, plotfile=None, **options):
			"""
			Plot dose volume histograms from argument `data`.

			Args:
				data (:obj:`dict`, or :class:`RunRecord`): Used to build
					the DVH curves. Assumed to be compatible with the
					`Case` used to initialize this object.
				second_pass (:obj:`bool`, optional): Plot data from
					second planning pass when ``True`` and ``data`` is a
					:class:`RunRecord`.
				show (:obj:`bool`, optional): Show figure after drawing.
				clear (:obj:`bool`, optional): Clear figure before
					rendering data in ``data``.
				subset (:obj:`list` or :obj:`tuple`, optional): Specify
					labels of DVH curves to be plotted; others are
					suppressed. All structures' DVH curves are plotted
					by default.
				plotfile (:obj:`str`, optional): Passed to to the
					:class:`DVHPlot` as a target filepath to save the
					drawn plot.
				**options: Arbitrary keyword arguments passed through to
					:meth:`~DVHPlot.plot`.

			Returns:
				None

			Raises:
				TypeError: If ``subset`` is specified but not a
					:obj:`list` or :obj:`tuple`.
				KeyError: If ``subset`` is specified but contains items
					that are not recognized as valid structure labels.
			"""
			if plotfile is None:
				plotfile = options.pop('file', None)
			if isinstance(data, RunRecord):
				if second_pass and data.plotting_data['exact'] is not None:
					data = data.plotting_data['exact']
				else:
					data = data.plotting_data[0]
			data_ = data

			# filter data to only plot DVH for structures with requested labels
			if subset is None:
				data = data_
			else:
				if not isinstance(subset, (list, tuple)):
					raise TypeError('argument "subset" must be of type {} or '
									'{}'.format(list, tuple))
				if not all([label in data_.keys() for label in subset]):
					raise KeyError('argument "subset" specifies an invalid '
								   'structure label')
				data = {}
				for label in subset:
					data[label] = data_[label]

			self.dvh_plot.plot(
					data,
					show=show,
					clear=clear,
					**options)
			if plotfile is not None:
				self.dvh_plot.save(plotfile)