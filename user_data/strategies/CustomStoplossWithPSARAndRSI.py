# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import IStrategy

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime
from freqtrade.persistence import Trade


class CustomStoplossWithPSARAndRSI(IStrategy):
    """
    Custom strategy with PSAR-based trailing stop loss and RSI filter for overbought/oversold conditions.
    """
    INTERFACE_VERSION: int = 3
    timeframe = '1h'
    stoploss = -0.2
    custom_info = {}
    use_custom_stoploss = True

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        result = 1
        if self.custom_info and pair in self.custom_info and trade:
            relative_sl = None
            if self.dp:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
                last_candle = dataframe.iloc[-1].squeeze()
                relative_sl = last_candle['sar']

            if relative_sl is not None:
                new_stoploss = (current_rate - relative_sl) / current_rate
                result = new_stoploss - 1

        return result

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds indicators to the DataFrame. Adds SAR and RSI.
        """
        dataframe['sar'] = ta.SAR(dataframe)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)  # RSI with a 14-period window

        if self.dp.runmode.value in ('backtest', 'hyperopt'):
            self.custom_info[metadata['pair']] = dataframe[['date', 'sar']].copy().set_index('date')

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Defines the entry conditions for a trade. Enters only if the RSI indicates oversold conditions.
        """
        dataframe.loc[
            (
                (dataframe['sar'] < dataframe['sar'].shift()) &  # SAR indicates uptrend
                (dataframe['rsi'] < 30)  # RSI indicates oversold
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Defines the exit conditions for a trade.
        """
        dataframe.loc[:, 'exit_long'] = 0
        return dataframe
