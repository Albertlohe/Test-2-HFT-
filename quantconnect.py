# region imports
from AlgorithmImports import *
# endregion

class CalculatingTanHornet(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 1, 1)
        self.set_cash(100000)
        
        # Trade liquid ETFs for fast execution
        self._symbols = [
            self.add_equity("SPY", Resolution.MINUTE).symbol,  # S&P 500
            self.add_equity("QQQ", Resolution.MINUTE).symbol,  # Nasdaq
            self.add_equity("IWM", Resolution.MINUTE).symbol,  # Russell 2000
            self.add_equity("DIA", Resolution.MINUTE).symbol,  # Dow Jones
        ]
        
        # Momentum indicators (RSI for overbought/oversold)
        self._rsi = {}
        self._momentum = {}
        self._sma = {}
        
        for symbol in self._symbols:
            self._rsi[symbol] = self.rsi(symbol, 14, MovingAverageType.WILDERS, Resolution.MINUTE)
            self._momentum[symbol] = self.momp(symbol, 20, Resolution.MINUTE)
            self._sma[symbol] = self.sma(symbol, 50, Resolution.MINUTE)
        
        # Strategy parameters
        self._rsi_oversold = 45  # More sensitive
        self._rsi_overbought = 55  # More sensitive
        self._momentum_threshold = 0.1  # Lower threshold
        self._max_position_size = 0.4  # Larger positions
        self._stop_loss_pct = 0.02  # 2% stop loss
        self._take_profit_pct = 0.03  # 3% take profit
        
        # Track entry prices for stop loss/take profit
        self._entry_prices = {}
        
        # Rebalance every 15 minutes during market hours
        self.schedule.on(self.date_rules.every_day(),
                        self.time_rules.every(timedelta(minutes=15)),
                        self.rebalance)
        
        # Set warmup to initialize indicators
        self.set_warmup(timedelta(days=5))
        self.settings.seed_initial_prices = True
    
    def rebalance(self):
        """Execute rebalancing logic with momentum signals."""
        if self.is_warming_up:
            return
        
        # Calculate momentum scores for ranking
        scores = {}
        
        for symbol in self._symbols:
            if not (self._rsi[symbol].is_ready and 
                   self._momentum[symbol].is_ready and 
                   self._sma[symbol].is_ready):
                continue
            
            rsi = self._rsi[symbol].current.value
            momentum = self._momentum[symbol].current.value
            price = self.securities[symbol].price
            sma = self._sma[symbol].current.value
            
            # Combined score: momentum + RSI deviation from 50 + trend
            rsi_score = (50 - rsi) / 50  # Negative when overbought
            trend_score = 1 if price > sma else -1
            combined_score = momentum + rsi_score + (trend_score * 0.5)
            
            scores[symbol] = combined_score
        
        # Rank symbols by score
        if not scores:
            return
        
        sorted_symbols = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Go long top 2, short bottom 2
        signals = {}
        for i, (symbol, score) in enumerate(sorted_symbols):
            if i < 2:  # Top 2 - long
                signals[symbol] = 1.0
            elif i >= len(sorted_symbols) - 2:  # Bottom 2 - short
                signals[symbol] = -1.0
            else:
                signals[symbol] = 0.0
        
        # Check stop loss and take profit on existing positions
        for symbol in self._symbols:
            if self.portfolio[symbol].invested and symbol in self._entry_prices:
                current_price = self.securities[symbol].price
                entry_price = self._entry_prices[symbol]
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Hit stop loss or take profit
                if pnl_pct < -self._stop_loss_pct or pnl_pct > self._take_profit_pct:
                    self.liquidate(symbol)
                    del self._entry_prices[symbol]
                    signals[symbol] = 0.0
        
        # Build portfolio targets
        targets = []
        long_count = sum(1 for s in signals.values() if s > 0)
        short_count = sum(1 for s in signals.values() if s < 0)
        
        long_weight = self._max_position_size if long_count > 0 else 0
        short_weight = -self._max_position_size if short_count > 0 else 0
        
        for symbol, signal in signals.items():
            if signal > 0:
                targets.append(PortfolioTarget(symbol, long_weight))
                if not self.portfolio[symbol].invested:
                    self._entry_prices[symbol] = self.securities[symbol].price
            elif signal < 0:
                targets.append(PortfolioTarget(symbol, short_weight))
                if not self.portfolio[symbol].invested:
                    self._entry_prices[symbol] = self.securities[symbol].price
            else:
                targets.append(PortfolioTarget(symbol, 0))
        
        # Execute all targets at once
            self.set_holdings(targets, liquidate_existing_holdings=True)
