from .tally_service import TallyService


class DashboardService:
    def __init__(self, tally: TallyService = None):
        self.tally = tally or TallyService()

    def get_today_sales(self):
        return self.tally.fetch_today_sales()

    def get_low_stock(self, threshold=10):
        return self.tally.fetch_low_stock(threshold=threshold)

    def get_pending_dues(self):
        # Placeholder: a real implementation would query ledgers/vouchers
        return {"pending": [], "note": "Implement ledger query via Tally XML"}
