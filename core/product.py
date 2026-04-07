class Batch:
    def __init__(self, arrival_date, quantity, expiry_date=None):
        self.arrival_date = arrival_date
        self.quantity = quantity
        self.expiry_date = expiry_date
