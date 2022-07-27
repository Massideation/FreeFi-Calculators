import numpy as np
import pandas as pd
import pandas_ta as ta

class TradingEnv:
    def __init__(self, balance_amount, balance_unit, trading_fee_multiplier,buy_percentage,sell_percentage,all_in_strategy=False):
        self.all_in : bool = all_in_strategy
        self.starting_balance : float  = balance_amount
        self.balance_amount : float = balance_amount
        self.balance_unit = balance_unit
        self.in_position : bool  = False
        self.positive_balance: bool = True
        self.trading_fee_multiplier = trading_fee_multiplier
        self.buy_percent=buy_percentage
        self.sell_percent=sell_percentage
        self.coin_qty : float  = 0.0
        
    def buy(self, buy_price, time):
        # calculatig amount to buy
        buy_amount=self.buy_percent * 0.01 * self.balance_amount
        # checking if balance is available
        if self.balance_amount >= buy_amount:

            # adjusting balance amount available in account
            self.balance_amount -= buy_amount 

            # adjusting qty of coin 
            self.coin_qty += buy_amount/(self.trading_fee_multiplier * buy_price)

            # changing position status
            self.in_position=True
        
        else :
            self.positive_balance = False


    def buy_all(self,buy_price,time):
        # all in
        buy_amount = self.balance_amount
        #    
        self.balance_amount -= buy_amount
        # adjusting qty of coin 
        self.coin_qty += buy_amount/(self.trading_fee_multiplier * buy_price)

        # changing position status
        self.in_position=True
        # 
        self.positive_balance =False



    def sell(self, sell_price, time):
        # determining the qyantity of coin to sell
        sell_qty= self.sell_percent * 0.01 * self.coin_qty
        # checking if coin balance vailable in account
        if sell_qty <= self.coin_qty:
            # adjusting the quantity of coin
            self.coin_qty -= sell_qty
            # adjusting balance amount available in account
            self.balance_amount += (sell_qty * sell_price * self.trading_fee_multiplier)

        elif self.coin_qty <= 0:
            self.in_position=False
        


    def sell_all(self,sell_price,time):
        sell_qty= self.coin_qty
        # selling all ther remaining coin
        self.coin_qty = 0.0
        # adjusting balance amount 
        self.balance_amount += (sell_qty * sell_price * self.trading_fee_multiplier)

        self.in_position=False

        self.positive_balance=True



