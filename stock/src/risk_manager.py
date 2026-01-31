"""
Risk Management for Trading System
Prevents account blowup, enforces position limits, stop losses
"""

from src.logger import logger


class RiskManager:
    """
    Manages position sizing, stops, and portfolio risk
    """
    
    def __init__(self, account_size: float = 100000, risk_per_trade: float = 0.02):
        """
        Initialize risk manager
        
        Args:
            account_size: Total trading capital (INR)
            risk_per_trade: Max % of account to risk per trade (default 2%)
        """
        self.account_size = account_size
        self.risk_per_trade = risk_per_trade
        self.open_trades = {}  # {symbol: {'entry': X, 'shares': Y, 'stop': Z, ...}}
        self.today_pnl = 0
        self.trade_count = 0
        
        logger.info(
            f"RiskManager: Account={account_size:,.0f}, "
            f"Risk/trade={risk_per_trade*100}%"
        )
    
    def can_enter_trade(self) -> tuple:
        """
        Check if we can enter new trade
        
        Returns:
            tuple: (bool: can_enter, str: reason)
        """
        # Max 5 concurrent trades
        if len(self.open_trades) >= 5:
            return False, "Max 5 concurrent trades reached"
        
        # Max 10 trades per day
        if self.trade_count >= 10:
            return False, "Max 10 trades per day reached"
        
        # Daily loss limit: -5% of account
        daily_loss_limit = self.account_size * -0.05
        if self.today_pnl < daily_loss_limit:
            return False, f"Daily loss limit hit: {self.today_pnl:,.0f}"
        
        return True, "Can enter"
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> int:
        """
        Calculate position size based on entry and stop loss
        
        Args:
            entry_price: Entry price per share
            stop_loss_price: Stop loss price per share
        
        Returns:
            int: Number of shares to buy
        """
        if entry_price <= 0 or stop_loss_price < 0:
            return 0
        
        # Risk amount in rupees
        risk_rupees = self.account_size * self.risk_per_trade
        
        # Price risk per share
        price_risk = abs(entry_price - stop_loss_price)
        if price_risk < 0.01:  # Prevent division by near-zero
            return 0
        
        # Position size
        shares = int(risk_rupees / price_risk)
        
        # Don't use more than 50% of account on single trade
        max_capital = self.account_size * 0.5
        capital_needed = shares * entry_price
        
        if capital_needed > max_capital:
            shares = int(max_capital / entry_price)
        
        logger.info(
            f"Position size: {shares} shares @ {entry_price:.2f} "
            f"(Stop: {stop_loss_price:.2f}, Risk: {price_risk*shares:,.0f})"
        )
        
        return max(0, shares)
    
    def record_entry(self, symbol: str, entry_price: float, shares: int, 
                     stop_loss: float, profit_target: float):
        """
        Record a new trade entry
        
        Args:
            symbol: Stock symbol
            entry_price: Entry price
            shares: Number of shares
            stop_loss: Stop loss price
            profit_target: Profit target price
        """
        self.open_trades[symbol] = {
            'entry': entry_price,
            'shares': shares,
            'stop': stop_loss,
            'target': profit_target,
            'risk': (entry_price - stop_loss) * shares,
            'reward': (profit_target - entry_price) * shares,
        }
        self.trade_count += 1
        
        logger.info(
            f"[{symbol}] ENTRY: {entry_price:.2f} × {shares} shares | "
            f"SL: {stop_loss:.2f} | PT: {profit_target:.2f}"
        )
    
    def check_exit(self, symbol: str, current_price: float) -> tuple:
        """
        Check if trade should exit
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
        
        Returns:
            tuple: (exit_reason, exit_price) or (None, None) if no exit
        """
        if symbol not in self.open_trades:
            return None, None
        
        trade = self.open_trades[symbol]
        stop = trade['stop']
        target = trade['target']
        
        # Check stop loss
        if current_price <= stop:
            pnl = (stop - trade['entry']) * trade['shares']
            self.today_pnl += pnl
            del self.open_trades[symbol]
            logger.info(f"[{symbol}] STOP LOSS @ {stop:.2f} | P&L: {pnl:,.0f}")
            return "STOP_LOSS", stop
        
        # Check profit target
        if current_price >= target:
            pnl = (target - trade['entry']) * trade['shares']
            self.today_pnl += pnl
            del self.open_trades[symbol]
            logger.info(f"[{symbol}] PROFIT TARGET @ {target:.2f} | P&L: {pnl:,.0f}")
            return "PROFIT_TARGET", target
        
        return None, None
    
    def summary(self):
        """Print daily summary"""
        print(f"\n{'='*60}")
        print(f"TRADING SUMMARY")
        print(f"{'='*60}")
        print(f"Account:      {self.account_size:>12,.0f}")
        print(f"Today P&L:    {self.today_pnl:>12,.0f}")
        print(f"Return %:     {(self.today_pnl/self.account_size)*100:>12.2f}%")
        print(f"Trades:       {self.trade_count:>12}")
        print(f"Open:         {len(self.open_trades):>12}")
        print(f"{'='*60}\n")
