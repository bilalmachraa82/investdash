class InvestDashError(Exception):
    """Base exception for InvestDash."""

    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)


class MarketDataError(InvestDashError):
    """Market data API failed and no cache available."""
    pass


class PortfolioError(InvestDashError):
    """Error reading or processing portfolio."""
    pass


class TradingError(InvestDashError):
    """Error executing trade."""
    pass


class TradingSafetyError(TradingError):
    """Trade blocked by safety rules."""
    pass


class CacheError(InvestDashError):
    """Error in cache layer."""
    pass


class AIEngineError(InvestDashError):
    """Error in AI engine."""
    pass
