"""
ShareX Settlement - Core Package
=================================
핵심 계산 엔진
"""

__all__ = [
    'ApportionmentEngine',
]

# Lazy import to avoid circular dependency issues
def __getattr__(name):
    if name == 'ApportionmentEngine':
        from .apportionment import ApportionmentEngine
        return ApportionmentEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
