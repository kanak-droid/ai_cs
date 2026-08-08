# MOCKED — replace with real API call.
#
# Real integration: this would call AstroLokal's finance/payroll service, e.g.
#   GET {SALARY_API_URL}/astrologers/{astrologer_id}/salary-details
# Nothing outside this file needs to change to make that swap.
from dataclasses import dataclass

from app.integrations.config import MOCK_MODE


@dataclass(frozen=True)
class SalaryDetails:
    astrologer_id: int
    monthly_salary_inr: int
    last_revision_date: str
    next_review_date: str


def get_salary_details(astrologer_id: int) -> SalaryDetails:
    if not MOCK_MODE:
        raise NotImplementedError("Real salary integration is not wired up yet.")

    return SalaryDetails(
        astrologer_id=astrologer_id,
        monthly_salary_inr=15000 + (astrologer_id * 311) % 25000,
        last_revision_date="2026-04-01",
        next_review_date="2026-10-01",
    )
