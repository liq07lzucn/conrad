from example_utils import *
from data_utils import line_integral_mat
from plot_utils import plot_structures

SHOW_STRUCTS = True
CALC_AMAT = False

n = 1000
# n = 10
m_grid = 10000
n_grid = 500

x_grid, y_grid, regions = simple_structures(m_grid, n_grid)

if SHOW_STRUCTS:
	struct_kw = simple_colormap()
	plot_structures(x_grid, y_grid, regions, **struct_kw)

if CALC_AMAT:
	A, beam_angles = line_integral_mat(theta_grid, regions, beam_angles = n, atol = 1e-3)
	# np.save("data/A_cardioid_rot_10000x500-grid_10-beams.npy", A)
	np.save("data/A_cardioid_rot_10000x500-grid_1000-beams.npy", A)