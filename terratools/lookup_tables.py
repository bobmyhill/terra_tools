import numpy as np
from scipy.interpolate import interp2d, interp1d
import os
import matplotlib.pyplot as plt


class SeismicLookupTable:
    def __init__(self, table_path):
        """
        Calling will create a dictionary (self.fields) containing
        fields given in seismic lookup table. Under each field are:

        - [0] : Table Index
        - [1] : Field gridded in T-P space
        - [2] : Units

        This also sets up interpolator objects (eg self.vp_interp)
        for rapid querying of points.

        Currently the input table must have the following structure, with rows
        ascending by pressure then temperature.

        | Pressure | Temperature | Vp | Vs | Vp_an | Vs_an | Vphi | Density | Qs | T_solidus |
        | -------- | ----------- | -- | -- | ----- | ----- | ---- | ------- | -- | --------- |
        | 0        | 500         |    |    |       |       |      |         |    |           |
        | 0        | 1000        |    |    |       |       |      |         |    |           |
        | 0        | 1500        |    |    |       |       |      |         |    |           |
        | 1e8      | 500         |    |    |       |       |      |         |    |           |
        | 1e8      | 1000        |    |    |       |       |      |         |    |           |
        | 1e8      | 1500        |    |    |       |       |      |         |    |           |

        :param table_path: Path to table file, e.g. '/path/to/data/table.dat'
        :type table_path: string

        :return: Lookup table object
        """
        try:
            self.table = np.genfromtxt(f"{table_path}")
        except:
            self.table = np.genfromtxt(f"{table_path}", skip_header=1)

        self.P = self.table[:, 0]
        self.T = self.table[:, 1]
        self.pres = np.unique(self.table[:, 0])
        self.temp = np.unique(self.table[:, 1])
        self.n_uniq_p = len(self.pres)
        self.n_uniq_t = len(self.temp)
        self.t_max = np.max(self.temp)
        self.t_min = np.min(self.temp)
        self.p_max = np.max(self.pres)
        self.p_min = np.min(self.pres)
        self.pstep = np.size(self.temp)

        # Initialise arrays for storing table columns in Temp-Pressure space
        Vp = np.zeros((len(self.temp), len(self.pres)))
        Vs = np.zeros((len(self.temp), len(self.pres)))
        Vp_an = np.zeros((len(self.temp), len(self.pres)))
        Vs_an = np.zeros((len(self.temp), len(self.pres)))
        Vphi = np.zeros((len(self.temp), len(self.pres)))
        Dens = np.zeros((len(self.temp), len(self.pres)))
        Qs = np.zeros((len(self.temp), len(self.pres)))
        T_sol = np.zeros((len(self.temp), len(self.pres)))

        # Fill arrays with table data
        for i, p in enumerate(self.pres):
            Vp[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 2
            ]
            Vs[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 3
            ]
            Vp_an[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 4
            ]
            Vs_an[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 5
            ]
            Vphi[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 6
            ]
            Dens[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 7
            ]
            Qs[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 8
            ]
            T_sol[:, i] = self.table[
                0 + (i * self.pstep) : self.pstep + (i * self.pstep), 9
            ]

        # Creat dictionary which holds the interpolator objects
        self.fields = {
            "vp": [2, Vp, "km/s"],
            "vs": [3, Vs, "km/s"],
            "vp_ani": [4, Vp_an, "km/s"],
            "vs_ani": [5, Vs_an, "km/s"],
            "vphi": [6, Vphi, "km/s"],
            "density": [7, Dens, "$kg/m^3$"],
            "qs": [8, Qs, "Hz"],
            "t_sol": [9, T_sol, "K"],
        }

        # Setup interpolator objects. These can be used for rapid querying of many individual points
        self.vp_interp = interp2d(self.pres, self.temp, Vp)
        self.vs_interp = interp2d(self.pres, self.temp, Vs)
        self.vp_an_interp = interp2d(self.pres, self.temp, Vp_an)
        self.vs_an_interp = interp2d(self.pres, self.temp, Vs_an)
        self.vphi_interp = interp2d(self.pres, self.temp, Vphi)
        self.density_interp = interp2d(self.pres, self.temp, Dens)
        self.qs_interp = interp2d(self.pres, self.temp, Qs)
        self.t_sol_interp = interp2d(self.pres, self.temp, T_sol)

    #################################################
    # Need to get temp, pres, comp at given point.
    # Pressure could come from PREM or from simulation
    # Comp will be in 3 component mechanical mixture
    # We will then find the
    #################################################

    def interp_grid(self, press, temps, field):
        """
        Routine for re-gridding lookup tables into new pressure-temperature space
        :param press: Pressures (Pa)
        :type press: float or numpy array
        :param temps: Temperatures (K)
        :type temps: float or numpy array
        :param field: Data field (eg. 'Vs')
        :type field: string

        :return: interpolated values of a given table property
                on a 2D grid defined by press and temps
        :rtype: 2D numpy array
        """

        press = [press] if type(press) == int or type(press) == float else press
        temps = [temps] if type(temps) == int or type(temps) == float else temps

        _check_bounds(press, self.pres, "pressure")
        _check_bounds(temps, self.temp, "temperature")

        grid = interp2d(self.pres, self.temp, self.fields[field.lower()][1])

        return grid(press, temps)

    def interp_points(self, press, temps, field):
        """
        Routine for interpolating gridded property data at one or more
        pressure-temperature points.

        :param press: Pressures (Pa)
        :type press: float or numpy array
        :param temps: Temperatures (K)
        :type temps: float or numpy array
        :param field: Data field (eg. 'Vs')
        :type field: string

        :return: interpolated values of a given table property
                at points defined by press and temps
        :rtype: 1D numpy array
        """

        # If integers are passed in then convert to indexable lists
        press = [press] if type(press) == int or type(press) == float else press
        temps = [temps] if type(temps) == int or type(temps) == float else temps

        _check_bounds(press, self.pres, "pressure")
        _check_bounds(temps, self.temp, "temperature")

        grid = interp2d(self.pres, self.temp, self.fields[field.lower()][1])

        out = np.zeros(len(press))
        for i in range(len(press)):
            out[i] = grid(press[i], temps[i])

        return out

    def plot_table(self, ax, field, cmap="viridis_r"):
        """
        Plots the lookup table as a grid with values coloured by
        value for the field given.

        :param ax: matplotlib axis object to plot on.
        :type ax: matplotlib axis object
        :param field: Data field (eg. 'Vs')
        :type field: string
        :param cmap: matplotlib colourmap.
        :type cmap: string

        :return: None

        """

        # get column index for field of interest
        units = self.fields[field.lower()][2]
        data = self.fields[field.lower()][1]

        # temperature on x axis
        data = data.transpose()
        print(data.shape)

        chart = ax.imshow(
            data,
            origin="lower",
            extent=[self.t_min, self.t_max, self.p_min, self.p_max],
            cmap=cmap,
            aspect="auto",
        )

        # chart = ax.tricontourf(self.P,self.T,self.table[:,i_field])

        plt.colorbar(chart, ax=ax, label=f"{field} ({units})")
        ax.set_xlabel("Temperature (K)")
        ax.set_ylabel("Pressure (Pa)")
        ax.set_title(f"P-T graph for {field}")
        ax.invert_yaxis()

    def plot_table_contour(self, ax, field, cmap="viridis_r"):
        """
        Plots the lookup table as contours using matplotlibs tricontourf.

        :param ax: matplotlib axis object to plot on.
        :type ax: matplotlib axis object
        :param field: Data field (eg. 'Vs')
        :type field: string
        :param cmap: matplotlib colourmap.
        :type cmap: string

        :return: None
        """

        # get column index for field of interest
        i_field = self.fields[field.lower()][0]
        units = self.fields[field.lower()][1]
        data = self.table[:, i_field]

        chart = ax.tricontourf(self.P, self.T, self.table[:, i_field], cmap=cmap)

        # chart = ax.tricontourf(self.P,self.T,self.table[:,i_field])

        plt.colorbar(chart, ax=ax, label=f"{field} ({units})")
        ax.set_ylabel("Temperature (K)")
        ax.set_xlabel("Pressure (Pa)")
        ax.set_title(f"P-T graph for {field}")


def harmonic_mean_comp(bas, lhz, hzb, bas_fr, lhz_fr, hzb_fr):
    """
    bas, lhz, hzb must be of equal length.
    This routine assumes 3 component mechanical mixture.

    :param bas: data for basaltic composition (eg. basalt.Vs)
    :param lhz: data for lherzolite composition
    :param hzb: data for harzburgite composition
    :param bas_fr: basalt fraction
    :param lhz_fr: lherzolite fraction
    :param hzb_fr: harzburgite fraction

    :return: harmonic mean of input values

    """
    m1 = (1.0 / bas) * bas_fr
    m2 = (1.0 / lhz) * lhz_fr
    m3 = (1.0 / hzb) * hzb_fr

    hmean = 1 / (m1 + m2 + m3)

    return hmean


def linear_interp_1d(vals1, vals2, c1, c2, cnew):
    """
    :param vals1: data for composition 1
    :param vals2: data for composition 2
    :param c1: C-value for composition 1
    :param c2: C-value for composition 2
    :param cnew: C-value(s) for new composition(s)

    :return: interpolated values for compositions cnew
    """

    interpolated = interp1d(
        np.array([c1, c2]),
        [vals1.flatten(), vals2.flatten()],
        fill_value="extrapolate",
        axis=0,
    )

    return interpolated(cnew)


def _check_bounds(input, check, TP):
    """
    :param input: values of interest
    :param check: range of table values
    :param TP:
    """

    if np.any(input[:] > np.max(check)):
        print(
            f"One or more of your {TP} inputs exceeds the table range, reverting to maximum table value"
        )

    if np.any(input[:] < np.min(check)):
        print(
            f"One or more of your {TP} inputs is below the table range, reverting to minimum table value"
        )
