import numpy as np
import pandas as pd


def square(arg):

    return np.sign(arg)*np.square(arg)


def linear(arg):
    return arg


def calc_solid_ice_discharge(forcing_temperature, parameters,
    initial_icesheet_vol, temp_sensitivity=square):

    """ solid ice discharge as used in Nauels et al. (2017, ERL).
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


def get_quantiles(slr_fitted, relative_to=2000):

    projection_quantiles = {}
    for scen in slr_fitted.keys():

        projections = pd.DataFrame(index=slr_fitted[scen]["1.22"].index,
                               columns=slr_fitted[scen].keys())

        for key, data in slr_fitted[scen].iteritems():
            projections.loc[:,key] = data.values

        projections -= projections.loc[relative_to,:]

        projection_quantiles[scen] = pd.DataFrame(
            index=projections.index,columns=[0.05,0.1667,0.5,0.8333,0.95])

        for quantile in projection_quantiles[scen].keys():
            projection_quantiles[scen].loc[:,quantile] = projections.quantile(quantile,axis=1)

    return projection_quantiles


def calc_solid_ice_discharge_nauels_gmd(forcing_temperature,voltotal,a,b,
                            temp_sensitivity=np.exp):

    """ OLD for reference:
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
