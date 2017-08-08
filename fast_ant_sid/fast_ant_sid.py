import numpy as np


def square(arg):

    return np.sign(arg)*np.square(arg)


def linear(arg):
    return arg


def calc_solid_ice_discharge(forcing_temperature, parameters,
    initial_icesheet_vol, temp_sensitivity=square):

    """ Solid ice discharge as used in Nauels et al. 2017, ERL, submitted.
    """

    sid_sens, fast_rate, temp0, temp_thresh = parameters

    def slow_discharge(volume, temperature, temp0, sid_sens):
        # negative rates mean ice volume loss
        return sid_sens*volume*temp_sensitivity(temperature-temp0)

    ## time spans forcing period
    time = np.arange(0,len(forcing_temperature),1)

    icesheet_vol = np.zeros_like(forcing_temperature)
    icesheet_vol[0] = initial_icesheet_vol
    slr_from_sid = np.zeros_like(forcing_temperature)

    # negative rates lead to sea level rise
    fast_sid = fast_rate*np.array(forcing_temperature > temp_thresh,
                                      dtype = np.float)

    for t in time[0:-1]:
        sid_slow = slow_discharge(icesheet_vol[t], forcing_temperature[t],
                                   temp0, sid_sens)

        # yearly discharge rate cannot be larger than remaining volume
        discharge = np.minimum(icesheet_vol[t], sid_slow+fast_sid[t])
        # positive sid rates mean ice volume loss
        icesheet_vol[t+1] = icesheet_vol[t] - discharge
        slr_from_sid[t+1] = initial_icesheet_vol - icesheet_vol[t+1]

    return slr_from_sid



def least_square_error(parameters, forcing, reference_data, max_volume_to_lose,
                       temp_sensitivity=square, anomaly_year=1950):

    """ handles several scenarios for one parameter set.
        We assume that there is one global maximum ice volume that can be lost
        (not dependent on parameter set.) """

    least_sq_error = np.zeros(len(reference_data.keys()))

    for i,scen in enumerate(reference_data.keys()):
        refdata = reference_data[scen]
        forc = forcing[scen]

        overlapping_indices = np.searchsorted(forc.index,refdata.index)

        # least square error between slr and
        # we here assume all ice can be lost until last year of simulation
        slr = calc_solid_ice_discharge(forc.values, parameters, max_volume_to_lose,
                                    temp_sensitivity=temp_sensitivity)

        # only use the years for optimization that overlap with reference data
        slr = slr[overlapping_indices]
        # relative to the year of DP16 reference start
        ref_index = np.where(refdata.index == anomaly_year)[0][0]
        slr = slr - slr[ref_index]
        # for normalizing the scenarios, i.e. making them more equally
        # important in the optimization
        max_slr_range_in_ref = refdata.max() - refdata.min()
        least_sq_error[i] = ((slr - refdata)**2.).sum()/max_slr_range_in_ref

    return least_sq_error.sum()


def calc_solid_ice_discharge_nauels_gmd(forcing_temperature,voltotal,a,b,
                            temp_sensitivity=np.exp):

    """ OLD: here for reference
    solid ice discharge as used in Nauels et al. 2017 for the
    Greenland solid ice discharge. Ice loss is exponentially dependent
    on the driving temperature in Nauels et al. 2017. """

    def discharge(volume, temperature, a, b):

        ds = - (a * volume * temp_sensitivity(b*temperature))
        return ds

    ## time spans forcing period
    time = np.arange(0,len(forcing_temperature),1)

    icesheet_vol = np.zeros_like(forcing_temperature)
    icesheet_vol[0] = voltotal
    solid_ice_discharge = np.zeros_like(forcing_temperature)
    slr = np.zeros_like(forcing_temperature)

    for t in time[0:-1]:
        ds = discharge(icesheet_vol[t], forcing_temperature[t], a, b)
        icesheet_vol[t+1] =  ds + icesheet_vol[t]
        solid_ice_discharge[t] = ds
        slr[t+1] = voltotal - icesheet_vol[t+1]

    return slr, solid_ice_discharge


def optimization():

    """ here only for reference, check the jupyter notebook for the
    functioning version. """

    sid_sens, fastrate, temp0, temp_thresh = 1.e-5, 20, 4., 4.
    bounds = ((0.,1.e-4),(0.,100.),(-2.,10.),(0.,10.))

    # determine maximum volume one time, (taken most sensitive run in year 2500)
    max_volume_to_lose = dp16_slr_mean["RCP85PIT"].max().max()

    parameters = (sid_sens, fastrate, temp0, temp_thresh)

    forcing = {scen:magicc_gmt[scen] for scen in magicc_gmt}

    parameters_ens = pd.DataFrame(columns=["sid_sens","fastrate","temp0","temp_thresh"])

    for i,member in enumerate(dp16_slr_mean["RCP26PIT"].keys()[:]):
        print member,
        try:
            reference_data = {"RCP26":dp16_slr_mean["RCP26PIT"][member],
                              "RCP45":dp16_slr_mean["RCP45PIT"][member],
                              "RCP85":dp16_slr_mean["RCP85PIT"][member]}
        except KeyError:
            reference_data = {"RCP26":dp16_slr_mean["RCP26PIT"][member],
                              "RCP85":dp16_slr_mean["RCP85PIT"][member]}

        parameters = mystic.scipy_optimize.fmin(fas.least_square_error, parameters,
                          args=(forcing,reference_data, max_volume_to_lose),
                          bounds=bounds, ftol = 1.e-5, maxiter = 10000, disp=0)

    #     OptimizeResult = optimize.minimize(fas.least_square_error, parameters,
    #                       args=(forcing,reference_data, max_volume_to_lose),
    #                       method="Nelder-Mead",
    #                       bounds=bounds, options={"maxiter":10000,"disp":True,"ftol":1.e-6})

    #     parameters = OptimizeResult.x
        parameters_ens.loc[member,:] = parameters
