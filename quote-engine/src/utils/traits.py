"""
Trait mappings for on-chain router integration.
Hardcoded trait mappings for pool and token traits.
"""

from typing import Dict, List


class TraitMappings:
    """Trait mappings for router contract integration"""
    
    # Pool trait mappings
    POOL_TRAITS = {
        "BTC-USDC-25": "dlmm-pool-btc-usdc-v-1-1",
        "BTC-USDC-50": "dlmm-pool-btc-usdc-v-1-1",
        "ETH-USDC-25": "dlmm-pool-eth-usdc-v-1-1",
        "BTC-ETH-25": "dlmm-pool-btc-eth-v-1-1",
        "SOL-USDC-25": "dlmm-pool-sol-usdc-v-1-1",
        "SOL-USDC-50": "dlmm-pool-sol-usdc-v-1-1",
        "ETH-USDC-50": "dlmm-pool-eth-usdc-v-1-1",
        "BTC-ETH-50": "dlmm-pool-btc-eth-v-1-1"
    }
    
    # Token trait mappings
    TOKEN_TRAITS = {
        "BTC": "sbtc-trait",
        "ETH": "seth-trait", 
        "USDC": "usdc-trait",
        "SOL": "sol-trait",
        "STX": "stx-trait",
        "DIKO": "diko-trait"
    }
    
    @classmethod
    def get_pool_trait(cls, pool_id: str) -> str:
        """Get pool trait for a given pool ID"""
        return cls.POOL_TRAITS.get(pool_id, "dlmm-pool-trait-v-1-1")
    
    @classmethod
    def get_token_trait(cls, token: str) -> str:
        """Get token trait for a given token"""
        return cls.TOKEN_TRAITS.get(token, f"{token.lower()}-trait")
    
    @classmethod
    def get_function_name(cls, swap_for_y: bool) -> str:
        """Get function name for swap direction"""
        return "swap-x-for-y" if swap_for_y else "swap-y-for-x"
    
    @classmethod
    def validate_pool_id(cls, pool_id: str) -> bool:
        """Validate if pool ID has a trait mapping"""
        return pool_id in cls.POOL_TRAITS
    
    @classmethod
    def validate_token(cls, token: str) -> bool:
        """Validate if token has a trait mapping"""
        return token in cls.TOKEN_TRAITS
    
    @classmethod
    def get_all_supported_tokens(cls) -> List[str]:
        """Get list of all supported tokens"""
        return list(cls.TOKEN_TRAITS.keys())
    
    @classmethod
    def get_all_supported_pools(cls) -> List[str]:
        """Get list of all supported pools"""
        return list(cls.POOL_TRAITS.keys()) 