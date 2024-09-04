from abc import ABC, abstractmethod
from functools import partial
from typing import Literal

import numpy as np
from pandas import DataFrame, concat

from AeroViz.process.core.SizeDist import SizeDist
from AeroViz.process.method import properties, internal, external, core_shell, sensitivity


class AbstractDistCalc(ABC):
    @abstractmethod
    def useApply(self) -> DataFrame:
        pass


class NumberDistCalc(AbstractDistCalc):
    def __init__(self, psd: SizeDist):
        self.psd = psd

    def useApply(self) -> DataFrame:
        """ Calculate number distribution """
        return self.psd.data


class SurfaceDistCalc(AbstractDistCalc):
    def __init__(self, psd: SizeDist):
        self.psd = psd

    def useApply(self) -> DataFrame:
        """ Calculate surface distribution """
        return self.psd.data.dropna().apply(lambda col: np.pi * self.psd.dp ** 2 * np.array(col),
                                            axis=1, result_type='broadcast').reindex(self.psd.index)


class VolumeDistCalc(AbstractDistCalc):
    def __init__(self, psd: SizeDist):
        self.psd = psd

    def useApply(self) -> DataFrame:
        """ Calculate volume distribution """
        return self.psd.data.dropna().apply(lambda col: np.pi / 6 * self.psd.dp ** 3 * np.array(col),
                                            axis=1, result_type='broadcast').reindex(self.psd.index)


class PropertiesDistCalc(AbstractDistCalc):
    def __init__(self, psd: SizeDist):
        self.psd = psd

    def useApply(self) -> DataFrame:
        """ Calculate properties of distribution """
        return self.psd.data.dropna().apply(partial(properties, dp=self.psd.dp, dlogdp=self.psd.dlogdp,
                                                    weighting=self.psd.weighting),
                                            axis=1, result_type='expand').reindex(self.psd.index)


class ExtinctionDistCalc(AbstractDistCalc):
    mapping = {'internal': internal,
               'external': external,
               'core_shell': core_shell,
               'sensitivity': sensitivity}

    def __init__(self,
                 psd: SizeDist,
                 RI: DataFrame,
                 method: Literal['internal', 'external', 'config-shell', 'sensitivity'],
                 result_type: Literal['extinction', 'scattering', 'absorption'] = 'extinction'
                 ):
        self.psd = psd
        self.RI = RI
        if method not in ExtinctionDistCalc.mapping:
            raise ValueError(f"Invalid method: {method}. Valid methods are: {list(ExtinctionDistCalc.mapping.keys())}")
        self.method = ExtinctionDistCalc.mapping[method]
        self.result_type = result_type

    def useApply(self) -> DataFrame:
        """ Calculate volume distribution """
        combined_data = concat([self.psd.data, self.RI], axis=1).dropna()
        return combined_data.apply(partial(self.method, dp=self.psd.dp, result_type=self.result_type),
                                   axis=1, result_type='expand').reindex(self.psd.index).set_axis(self.psd.dp, axis=1)


# TODO:
class LungDepositsDistCalc(AbstractDistCalc):

    def __init__(self, psd: SizeDist, lung_curve):
        self.psd = psd
        self.lung_curve = lung_curve

    def useApply(self) -> DataFrame:
        pass


class DistributionCalculator:  # 策略模式 (Strategy Pattern)
    """ Interface for distribution calculator """

    mapping = {'number': NumberDistCalc,
               'surface': SurfaceDistCalc,
               'volume': VolumeDistCalc,
               'property': PropertiesDistCalc,
               'extinction': ExtinctionDistCalc,
               'lung_deposit': LungDepositsDistCalc}

    def __init__(self,
                 calculator: Literal['number', 'surface', 'volume', 'property', 'extinction'],
                 psd: SizeDist,
                 RI: DataFrame = None,
                 method: str = None,
                 result_type: str = None
                 ):
        """
        Initialize the DistributionCalculator.

        Parameters:
        calculator (CalculatorType): The type of calculator.
        psd (SizeDist): The particle size distribution data.
        RI (Optional[DataFrame]): The refractive index data. Default is None.
        method (Optional[str]): The method to use. Default is None.
        result_type (Optional[str]): The result type. Default is None.
        """
        if calculator not in DistributionCalculator.mapping.keys():
            raise ValueError(
                f"Invalid calculator: {calculator}. Valid calculators are: {list(DistributionCalculator.mapping.keys())}")
        self.calculator = DistributionCalculator.mapping[calculator]
        self.psd = psd
        self.RI = RI
        self.method = method
        self.result_type = result_type

    def useApply(self) -> DataFrame:
        """
        Apply the calculator to the data.

        Returns:
        DataFrame: The calculated data.
        """
        if self.RI is not None:
            return self.calculator(self.psd, self.RI, self.method, self.result_type).useApply()
        elif issubclass(self.calculator, (NumberDistCalc, SurfaceDistCalc, VolumeDistCalc, PropertiesDistCalc)):
            return self.calculator(self.psd).useApply()
        else:
            raise ValueError("RI parameter is required for this calculator type")
