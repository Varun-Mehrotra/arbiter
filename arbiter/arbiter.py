import time
from socket import timeout
from datetime import datetime


class Arbiter():
    def __init__(self, public_exchange, private_exchange):
        """
        Setup two separate exchange objects so we can use separate rate
        limiting, as typically, private calls are have much harsher limits
        than public calls.
        """
        self.pub_exg = public_exchange
        self.prv_exg = private_exchange

    def wait_for_order_and_get_filled(self, order_id, timeout=5):
        epoch_timeout = time.time()*1000 + timeout*1000

        while(True):
            order = self.prv_exg.fetch_order(order_id)
            if order["status"] == "rejected":
                print(order)
                raise OrderRejectedError()

            if order["status"] == "closed":
                return order["filled"]

            if epoch_timeout < time.time()*1000:
                raise OrderTimeoutError()

    def get_crypto_combinations(self, market_symbols, base):
        markets = self.pub_exg.fetchMarkets()

        market_symbols = [market['symbol'] for market in markets]

        combinations = []
        for sym1 in market_symbols:

            sym1_token1 = sym1.split('/')[0]
            sym1_token2 = sym1.split('/')[1]
            if (sym1_token2 == base):
                for sym2 in market_symbols:
                    sym2_token1 = sym2.split('/')[0]
                    sym2_token2 = sym2.split('/')[1]
                    if (sym1_token1 == sym2_token2):
                        for sym3 in market_symbols:
                            sym3_token1 = sym3.split('/')[0]
                            sym3_token2 = sym3.split('/')[1]
                            if((sym2_token1 == sym3_token1)
                                    and (sym3_token2 == sym1_token2)):
                                combination = {
                                    'base': sym1_token2,
                                    'intermediate': sym1_token1,
                                    'ticker': sym2_token1,
                                }
                                combinations.append(combination)
        return combinations

    def fetch_current_ticker_price(self, ticker):
        current_ticker_details = self.pub_exg.fetch_ticker(ticker)
        if current_ticker_details is not None:
            ticker_price = current_ticker_details['ask']
        else:
            raise InvalidDetailsError()
        return ticker_price

    def check_return_buy_buy_sell(self, sym1, sym2, sym3):
        """
        Function returns the rate of return ignoring all costs.
        """
        # Just check if it's a profitable swap, ignore concrete amounts.
        current_price1 = self.fetch_current_ticker_price(sym1)
        current_price2 = self.fetch_current_ticker_price(sym2)
        current_price3 = self.fetch_current_ticker_price(sym3)

        return ((1 / current_price1)/current_price2)*current_price3

    def check_return_buy_sell_sell(self, sym1, sym2, sym3):
        """
        Function returns the rate of return ignoring all costs.
        """
        # Just check if it's a profitable swap, ignore concrete amounts.
        current_price1 = self.fetch_current_ticker_price(sym1)
        current_price2 = self.fetch_current_ticker_price(sym2)
        current_price3 = self.fetch_current_ticker_price(sym3)

        return (1 / current_price3)*current_price2*current_price1

    def place_sell_all_order(self, scrip):
        currency = scrip.split("/")[0]
        print(currency)
        order = self.prv_exg.create_market_sell_order(
            scrip,
            self.prv_exg.amount_to_precision(
                scrip, self.prv_exg.fetch_free_balance()[currency]
            )
        )
        # print(order)
        return order

    def place_buy_all_order(self, scrip):
        currency = scrip.split("/")[1]
        print(currency)
        order = self.prv_exg.create_market_buy_order(
            scrip,
            self.prv_exg.amount_to_precision(
                scrip, float(str(self.prv_exg.fetch_free_balance()[currency]/self.fetch_current_ticker_price(scrip))[:-1])
            )
        )
        # print(order)
        return order

    def place_trade_buy_buy_sell(self, sym1, sym2, sym3):
        final_amount = 0.0
        s1_order = {}

        for attempt in range(5):
            try:
                s1_order = self.place_buy_all_order(sym1)
                self.wait_for_order_and_get_filled(s1_order["id"])
                break
            except OrderRejectedError:
                print(f"Retrying Buy... Attempt #{attempt}")

        s2_order = {}
        for attempt in range(5):
            try:
                s2_order = self.place_buy_all_order(sym2)
                self.wait_for_order_and_get_filled(s2_order["id"])
                break
            except OrderRejectedError:
                print(f"Retrying Buy... Attempt #{attempt}")

        s3_order = self.place_sell_all_order(sym3)
        final_amount = self.wait_for_order_and_get_filled(s3_order["id"])

        return final_amount

    def place_trade_buy_sell_sell(self, sym1, sym2, sym3):
        final_amount = 0.0
        s3_order = {}

        for attempt in range(5):
            try:
                s3_order = self.place_buy_all_order(sym3)
                self.wait_for_order_and_get_filled(s3_order["id"])
                break
            except OrderRejectedError:
                print(f"Retrying Buy... Attempt #{attempt}")

        s2_order = self.place_sell_all_order(sym2)
        self.wait_for_order_and_get_filled(s2_order["id"])

        s1_order = self.place_sell_all_order(sym1)
        final_amount = self.wait_for_order_and_get_filled(s1_order["id"])

        return final_amount

    def execute_triangular_arbitrage(self, sym1, sym2, sym3, transaction_fee, min_profit_percent):
        total_val = (self.check_return_buy_buy_sell(sym1, sym2, sym3) - transaction_fee*3)
        while(total_val - 1 >= min_profit_percent):  # Be sticky! Keep this going, unless the profit falls.
            print(f"{datetime.now().strftime('%H:%M:%S')}-FOUND_OPPORTUNITY:"
                  f"BUY_BUY_SELL, {sym1},{sym2},{sym3}, Quotient: {total_val} ")
            final_amount = self.place_trade_buy_buy_sell(sym1, sym2, sym3)
            print(f"{datetime.now().strftime('%H:%M:%S')}-REALIZED_PROFIT:"
                  f"BUY_BUY_SELL, {sym1},{sym2},{sym3}, Total: {final_amount} ")
            total_val = (self.check_return_buy_buy_sell(sym1, sym2, sym3) - transaction_fee*3)

        # Can't derive this val from the one above, markets typically fluctuate too quickly
        total_val = (self.check_return_buy_sell_sell(sym1, sym2, sym3) - transaction_fee*3)
        while(total_val - 1 >= min_profit_percent):  # Be sticky! Keep this going, unless the profit falls.
            print(f"{datetime.now().strftime('%H:%M:%S')}-FOUND_OPPORTUNITY:"
                  f"BUY_SELL_SELL, {sym1},{sym2},{sym3}, Quotient: {total_val} ")
            final_amount = self.place_trade_buy_sell_sell(sym1, sym2, sym3)
            print(f"{datetime.now().strftime('%H:%M:%S')}-REALIZED_PROFIT:"
                  f"BUY_SELL_SELL, {sym1},{sym2},{sym3}, Total: {final_amount} ")
            total_val = (self.check_return_buy_sell_sell(sym1, sym2, sym3) - transaction_fee*3)

    def triangular_listener(self, base_currency, fee_percent, min_profit):

        markets = self.pub_exg.fetch_markets()
        market_symbols = [market['symbol'] for market in markets]
        market_symbols = [symbol for symbol in market_symbols if ":" not in symbol]
        market_symbols = [symbol for symbol in market_symbols if "SDN" not in symbol]

        combinations = self.get_crypto_combinations(market_symbols, base_currency)
        print(f"{datetime.now().strftime('%H:%M:%S')}-STARTED-RUN:"
              f"BASE CURRENCY {base_currency}, TRADING FEE {fee_percent*100}, MINIMUM PROFIT PERCENT {min_profit*100} ")
        while(True):
            try:
            # print(f"{datetime.now().strftime('%H:%M:%S')}-STARTING ARBITRAGE:")
                for combination in combinations:
                    base = combination['base']
                    intermediate = combination['intermediate']
                    ticker = combination['ticker']

                    s1 = f'{intermediate}/{base}'    # Eg: BTC/USDT
                    s2 = f'{ticker}/{intermediate}'  # Eg: ETH/BTC
                    s3 = f'{ticker}/{base}'          # Eg: ETH/USDT

                    self.execute_triangular_arbitrage(
                        s1, s2, s3,
                        fee_percent,
                        min_profit
                    )
            except timeout as err:
                print(f"{datetime.now().strftime('%H:%M:%S')}-EXCEPTION_OCCURED:"
                      f"Unexpected {err=}, {type(err)=} ")

class OrderTimeoutError(Exception):
    """Base class for other exceptions"""
    pass


class OrderRejectedError(Exception):
    """Base class for other exceptions"""
    pass


class InvalidDetailsError(Exception):
    """Raised when order information is invalid"""
    pass
