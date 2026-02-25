class measuredOrangeFiash(self):
    def Initialize(self):
        self.SetStartDate(2020,1,1)
        self.SetEndDate(2021,12,31)
        self.SetCash(100000)

        spy =self.AddEquity("SPY", Resolution.Daily)

        spy.SetDataNormalizationMode(DataNormalizationMode.Raw)

        self.spy = spy.Symbol

        self.Setbenchmark("Spy")
        self.setbrokageModel(BrokageName.Interactivebrokersbrokerage, accountType.Margin)

        self.entryprice = 0
        self.period = timedelta(31)
        self.nextentrytime = self.Time

    def OnData(self, data):
        if not self.spy in data:
            return

        #price = data[self.spy].Close
        price = data[self.spy].Close

        if not self.Portfolio.Invested:
            if self.nextentrytime <= self.Time:
                self.SetHoldings(self.spy, 1)
                #self.MarketOrder(self.spy, int(self.Portfolio.Cash / price))
                self.log("BUY SPY@" + str(price))  
                self.entryprice = price
                self.nextentrytime = self.Time + self.period

                elif self.entryPrice * 1.1 <= price or self.price * 0.9 >= price:
                    self.Liquidate(self.spy)
                    self.log("SELL SPY@" + str(price))
                self.nextentryTime = self.Time + self.period 
