#  -*- coding: utf-8 -*-
#  vim: tabstop=4 shiftwidth=4 softtabstop=4

#  Copyright (c) 2014, GEM Foundation

#  OpenQuake is free software: you can redistribute it and/or modify it
#  under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  OpenQuake is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU Affero General Public License
#  along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.

import numpy

from openquake.baselib import general
from openquake.commonlib import parallel
from openquake.calculators import base

F32 = numpy.float32

bcr_dt = numpy.dtype([('annual_loss_orig', F32), ('annual_loss_retro', F32),
                      ('bcr', F32)])


@parallel.litetask
def classical_bcr(riskinputs, riskmodel, rlzs_assoc, monitor):
    """
    Compute and return the average losses for each asset.

    :param riskinputs:
        a list of :class:`openquake.risklib.riskinput.RiskInput` objects
    :param riskmodel:
        a :class:`openquake.risklib.riskinput.RiskModel` instance
    :param rlzs_assoc:
        associations (trt_id, gsim) -> realizations
    :param monitor:
        :class:`openquake.baselib.performance.PerformanceMonitor` instance
    """
    result = {}  # (N, R) -> data
    lti = riskmodel.lti  # loss_type -> index
    for out_by_rlz in riskmodel.gen_outputs(riskinputs, rlzs_assoc, monitor):
        for out in out_by_rlz:
            for asset, (eal_orig, eal_retro, bcr) in zip(out.assets, out.data):
                aval = asset.value(out.loss_type)
                result[asset.aid, lti[out.loss_type], out.hid] = numpy.array([
                    (eal_orig * aval, eal_retro * aval, bcr)], bcr_dt)
    return result


@base.calculators.add('classical_bcr')
class ClassicalBCRCalculator(base.calculators['classical_risk']):
    """
    Classical BCR Risk calculator
    """
    core_func = classical_bcr

    def post_execute(self, result):
        zeros = numpy.zeros((self.N, self.L, self.R), bcr_dt)
        for nlr, data in result.items():
            zeros[nlr] = data
        self.datastore['bcr-rlzs'] = zeros
