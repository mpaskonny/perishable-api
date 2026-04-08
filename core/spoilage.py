from abc import ABC, abstractmethod


class SpoilageStrategy(ABC):
    @abstractmethod
    def calculate_spoilage(self, batch, current_date):
        pass


class StrictExpirySpoilage(SpoilageStrategy):
    def calculate_spoilage(self, batch, current_date):
        if batch.expiry_date and batch.expiry_date <= current_date:
            return batch.quantity
        return 0
