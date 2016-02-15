from time import time
from hashlib import sha1
from warnings import warn
from numpy import zeros, linspace

class Constraint(object):
	def __init__(self):
		self.__dose = 0.
		self.__threshold = None
		self.__direction = '<>'
		self.__slack = 0.
		self.__priority = 0

	
	@property
	def threshold(self):
		return self.__threshold

	@threshold.setter
	def threshold(self, threshold):
		self.__threshold = threshold

	@property
	def direction(self):
		return self.__direction
	
	@direction.setter
	def direction(self, direction):
		if self.threshold == 'max' and '>' in direction:
			self.__direction = '<'
			warn(Warning('constraint of form "Dmax > x Gy" '
				'not allowed, setting direction to "<"'))
			return
		if self.threshold == 'min' and '<' in direction:
			self.__direction = '>'
			warn(Warning('constraint of form "Dmin < x Gy" '
				'not allowed, setting direction to ">"'))
			return

		elif direction in ('<', '<='):
			self.__direction = '<'
		elif direction in ('>', '>='):
			self.__direction = '>'
		else:
			ValueError('argument "direction" must be'
				'one of ("<", "<=", ">", ">=")')

	@property
	def upper(self):
		return self.__direction == '<'

	@property
	def dose(self):
		return self.__dose

	@dose.setter
	def dose(self, dose):
		if isinstance(dose, (int, float)):
			self.__dose = max(float(dose), 0.)
		else:
			TypeError('argument "dose" must be'
				'of type "int" or "float"')

	@property
	def slack(self):
	    return self.__slack
	
	@slack.setter
	def slack(self, slack):
		if isinstance(slack, (int, float)):
			if slack < 0:
				warn(Warning('argument "slack" must be '
					'nonnegative; setting to zero'))
			self.__slack = max(0., float(slack))
		else:
			TypeError('argument "slack" must be '
				'of type float with value >= 0')		

	@property
	def dose_achieved(self):
		sign = +1 if self.upper else -1
		return self.__dose + sign * self.__slack

	@property
	def priority(self):
		return self.__priority

	@priority.setter
	def priority(self, priority):
		if isinstance(priority, (int, float)):
			self.__priority = max(0, min(3, int(priority)))
			if priority < 0:
				warn(Warning('argument "priority" cannot be negative, '
					'setting to 0'))
			elif priority > 3:
				warn(Warning('argument "priority" cannot be > 3, '
					'setting to 3'))
		else:
			TypeError('argument "priority" must be '
				'an integer between 0 and 3')

	def __le__(self, other):
		self.direction = '<'
		self.dose = other
		return self

	def __lt__(self, other):
		return self.__le__(other)

	def __ge__(self, other):
		self.direction = '>'
		self.dose = other
		return self

	def __gt__(self, other):
		return self.__le__(other)

	def __str__(self):
		return str('D{} {}= {}Gy'.format(
			str(self.__threshold),
			str(self.__direction),
			str(self.__dose)))
	
class PercentileConstraint(Constraint):
	def __init__(self, percentile = None, direction = None, dose = None):
		Constraint.__init__(self)
		self.direction = direction
		self.dose = dose
		if percentile is not None:
			self.percentile = percentile

	@property
	def percentile(self):
		return self.threshold

	@percentile.setter
	def percentile(self, percentile):
		if isinstance(percentile, (int, float)):
			self.threshold = min(100., max(0., float(percentile)))
		else:
			TypeError('argument "percentile" must be of type int or float')

	@property
	def plotting_data(self):
		return {'type': 'percentile',
			'percentile' : 2 * [self.percentile], 
			'dose' :[self.dose, self.dose_achieved], 
			'symbol' : self.direction}

	def get_maxmargin_fulfillers(self, y, had_slack = False):
		""" 
		given dose vector y, get the indices of the voxels that
		fulfill this dose constraint (self) with maximum margin

		given len(y), if m voxels are required to respect the
		dose constraint exactly, y is assumed to contain 
		at least m entries that respect the constraint
		(for instance, y is generated by a convex program
		that includes a convex restriction of the dose constraint)


		procedure:
		- get margins: (y - self.dose_requested)
		- sort margin indices by margin values 
		- if upper bound, return indices of p most negative entries 
			(first p of sorted indices; numpy.sort sorts small to large)
		- if lower bound, return indices p most positive entries 
			(last p of sorted indices; numpy.sort sorts small to large)
		
		p = percent non-violating * structure size
			= percent non-violating * len(y)

		"""

		fraction = self.percentile / 100.
		non_viol = (1 - fraction) if self.upper else fraction
		n_returned = int(non_viol * len(y))

		start = 0 if self.upper else -n_returned
		end = n_returned if self.upper else -1
		dose = self.dose_achieved if had_slack else self.dose
		return (y - dose).argsort()[start:end]


class MeanConstraint(Constraint):
	def __init__(self, direction = None, dose = None):
		Constraint.__init__(self)
		self.direction = direction
		self.dose = dose
		self.threshold = 'mean'

	@property
	def plotting_data(self):
		return {'type': 'mean',
			'dose' :[self.dose, self.dose_achieved], 
			'symbol' : self.direction}

class MinConstraint(Constraint):
	def __init__(self, direction = None, dose = None):
		Constraint.__init__(self)
		self.direction = direction
		self.dose = dose
		self.threshold = 'min'

	@property
	def plotting_data(self):
		return {'type': 'min',
			'dose' :[self.dose, self.dose_achieved], 
			'symbol' : self.direction}

class MaxConstraint(Constraint):
	def __init__(self, direction = None, dose = None):
		Constraint.__init__(self)
		self.direction = direction
		self.dose = dose
		self.threshold = 'max'

	@property
	def plotting_data(self):
		return {'type': 'max',
			'dose' :[self.dose, self.dose_achieved], 
			'symbol' : self.direction}

def D(threshold, direction = None, dose = None):
	if threshold in ('mean', 'Mean'):
		return MeanConstraint(direction = direction, dose = dose)
	elif threshold in ('min', 'Min', 'minimum', 'Minimum') or threshold == 100:
		return MinConstraint(direction = direction, dose = dose)
	elif threshold in ('max', 'Max', 'maximum', 'Maximum') or threshold == 0:
		return MaxConstraint(direction = direction, dose = dose)
	elif isinstance(threshold, (int, float)):
		return PercentileConstraint(percentile = threshold, direction = direction, dose = dose)
	else:
		ValueError('constraint unparsable as phrased')

class ConstraintList(object):
	def __init__(self):
		self.items = {}
		self.last_key = None

	@staticmethod
	def __keygen(constraint):
		return sha1(str(time()) + str(constraint.dose) + 
			str(constraint.threshold) + 
			str(constraint.direction)).hexdigest()[:6]
	
	def __getitem__(self, key):
		return self.items[key]

	def __iter__(self):
		return self.items.__iter__()

	# TODO: __next__ for python 3.x
	def next(self):
		return self.items.next()

	def iteritems(self):
		return self.items.iteritems()

	def itervalues(self):
		return self.items.itervalues()

	def __iadd__(self, other):
		if isinstance(other, Constraint):
			key = self.__keygen(other)
			self.items[key] =  other
			self.last_key = key
			return self
		elif isinstance(other, ConstraintList):
			for constr in other.items.itervalues():
				self += constr
			return self
		else:
			TypeError('argument must be of '
				'type {} or {}'.format(
					Constraint, ConstraintList))

	def __isub__(self, other):
		if isinstance(other, Constraint):
			for key, constr in self.items.iteritems():
				if other == constr:
					del self.items[key] 
					return self
		else:
			if other in self.items:
				del self.items[other]
				return self

	@property
	def size(self):
	    return len(self.items.keys())
	
	@property
	def mean_only(self):
		meantest = lambda c : isinstance(c, MeanConstraint)

		if self.size == 0:
			return True
		else:
			return all(map(meantest, self.itervalues()))

	def clear(self):
		self.items = {}

	@property
	def plotting_data(self):
		return [(key, dc.plotting_data) for key, dc in self.items.iteritems()]

	def __str__(self):
		out = '(keys):\t (constraints)\n'
		for key, constr in self.items.iteritems():
			out += key + ':\t' + str(constr) + '\n'
		return out

class DVH(object):
	""" 
	TODO: DVHCurve docstring
	"""

	MAX_LENGTH = 1000

	def __init__(self, n_voxels, maxlength = MAX_LENGTH):
		""" TODO: docstring """
		self.__dose_buffer = zeros(n_voxels)
		self.__stride = 1 * (n_voxels <= maxlength) + n_voxels / maxlength
		length = len(self.__dose_buffer[::self.__stride]) + 1
		self.__doses = zeros(length)
		self.__percentiles = zeros(length)
		self.__percentiles[0] = 100.
		self.__percentiles[1:] = linspace(100, 0, length - 1)
		self.__DATA_SET__ = False

	@property
	def data(self):
	    return self.__doses[1:]
	
	@data.setter
	def data(self, y):
		""" TODO: docstring """
		if len(y) != self.__dose_buffer.size:
			ValueError('dimension mismatch: length of argument "y" '
				'must be {}'.format(self.__dose_buffer.size))

		self.__dose_buffer[:] = y[:]
		self.__dose_buffer.sort()
		self.__doses[1:] = self.__dose_buffer[::self.__stride]
		self.__DATA_SET__ = True

	@staticmethod
	def __interpolate_percentile(p1, p2, p_des):
		""" TODO: docstring """
		# alpha * p1 + (1 - alpha) * p2 = p_des
		# (p1 - p2) * alpha = p_des - p2
		# alpha = (p_des - p2) / (p1 - p2)
		return (p_des - p2) / (p1 - p2)

	def dose_at_percentile(self, percentile):
		""" TODO: docstring """
		if self.__doses is None: return nan

		if percentile == 100: return self.min_dose
		if percentile == 0: return self.max_dose

		# bisection retrieval of dose @ percentile
 		u = len(self.__percentiles) - 1
		l = 1
		i = l + (u - l) / 2

		# set tolerance based on bucket width
		tol = (self.__percentiles[-2] - self.__percentiles[-1]) / 2

		# get to within 0.5 of a percentile if possible
		abstol = 0.5

		while (u - l > 5):
			# percentile sorted descending
			if self.__percentiles[i] > percentile:
				l = i				
			else:
				u = i
			i = l + (u - l) / 2

		# break to iterative search
		idx = None
		for i in xrange(l, u):
			if abs(self.__percentiles[i] - percentile) < tol:
				idx = i
				break

		if idx is None: idx = u
		if tol <= abstol or abs(self.__percentiles[idx] - percentile) <= abstol:
			# return dose if available percentile bucket is close enough
			return self.__doses[idx]
		else:
			# interpolate dose by interpolating percentiles if not close enough
			alpha = self.__interpolate_percentile(self.__percentiles[i], 
				self.__percentiles[i + 1], percentile)
			return alpha * self.__doses[i] + (1 - alpha) * self.__doses[i + 1]

	@property
	def min_dose(self):
		""" TODO: docstring """
		if self.__doses is None: return nan
		return self.__doses[1]

	@property
	def max_dose(self):
		""" TODO: docstring """
		if self.__doses is None: return nan
		return self.__doses[-1]
	

	@property
	def plotting_data(self):
		""" TODO: docstring """
		return {'percentile' : self.__percentiles, 'dose' : self.__doses}