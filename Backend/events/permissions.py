"""Compatibility import; staff flags alone no longer grant administration access."""
from accounts.permissions import IsAdministrator

IsAuthenticatedStaff = IsAdministrator
